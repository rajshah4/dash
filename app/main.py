"""
Dash API
========

Production deployment entry point for Dash.
Provides a FastAPI server with /chat, /sessions, and /health endpoints.

Features:
- Persistent conversations (saved to disk, resumable by session_id)
- Security confirmation policy (optional)
- LRU session eviction with in-flight protection
- Per-session locking to prevent concurrent corruption
- Configurable timeout on agent execution
- Graceful shutdown via lifespan

Run:
    python -m app.main
"""

import asyncio
import logging
import threading
import time
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from os import getenv
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from openhands.sdk import Conversation
from openhands.sdk.conversation.response_utils import get_agent_final_response

from dash.agents import confirmation_policy, dash
from dash.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

PERSISTENCE_DIR = Path(getenv("DASH_PERSISTENCE_DIR", str(PROJECT_ROOT / ".dash_sessions")))
ENABLE_CONFIRMATION = getenv("DASH_ENABLE_CONFIRMATION", "false").lower() == "true"
MAX_SESSIONS = int(getenv("DASH_MAX_SESSIONS", "100"))
SESSION_TTL_SECONDS = int(getenv("DASH_SESSION_TTL", str(60 * 60)))  # 1 hour default
CHAT_TIMEOUT_SECONDS = int(getenv("DASH_CHAT_TIMEOUT", "300"))  # 5 min default


# ============================================================================
# Session management with per-session locking + LRU eviction
# ============================================================================


class _SessionEntry:
    """Wraps a Conversation with a per-session lock and atomic in-flight counter."""

    __slots__ = ("conversation", "lock", "last_used", "_in_flight_lock", "_in_flight")

    def __init__(self, conversation: Conversation) -> None:
        self.conversation = conversation
        self.lock = threading.Lock()  # serialises requests to the same session
        self.last_used = time.monotonic()
        self._in_flight_lock = threading.Lock()  # guards the counter
        self._in_flight = 0

    def touch(self) -> None:
        self.last_used = time.monotonic()

    def acquire_flight(self) -> None:
        with self._in_flight_lock:
            self._in_flight += 1

    def release_flight(self) -> None:
        with self._in_flight_lock:
            self._in_flight -= 1

    @property
    def in_flight(self) -> int:
        with self._in_flight_lock:
            return self._in_flight


_sessions: OrderedDict[str, _SessionEntry] = OrderedDict()
_sessions_lock = threading.Lock()


def _evict_stale_sessions() -> None:
    """Remove idle sessions that exceed TTL or the max count (LRU).

    Sessions with in-flight requests are never evicted.
    """
    now = time.monotonic()
    with _sessions_lock:
        # Evict expired idle sessions
        expired = [
            sid
            for sid, entry in _sessions.items()
            if entry.in_flight == 0 and now - entry.last_used > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            entry = _sessions.pop(sid)
            try:
                entry.conversation.close()
            except Exception:
                pass

        # Evict oldest idle sessions if over capacity
        while len(_sessions) > MAX_SESSIONS:
            evicted = False
            for sid, entry in list(_sessions.items()):
                if entry.in_flight == 0:
                    _sessions.pop(sid)
                    try:
                        entry.conversation.close()
                    except Exception:
                        pass
                    evicted = True
                    break
            if not evicted:
                break  # all sessions are in-flight, can't evict


def _close_all_sessions() -> None:
    """Close every session — called during graceful shutdown."""
    with _sessions_lock:
        for sid, entry in list(_sessions.items()):
            try:
                entry.conversation.close()
            except Exception:
                logger.warning("Error closing session %s on shutdown", sid, exc_info=True)
        _sessions.clear()


def _get_or_create_session(session_id: str | None) -> tuple[_SessionEntry, str]:
    """Get an existing session or create a new one with persistence."""
    _evict_stale_sessions()

    with _sessions_lock:
        if session_id and session_id in _sessions:
            entry = _sessions[session_id]
            _sessions.move_to_end(session_id)  # refresh LRU position
            entry.touch()
            return entry, session_id

    # Create new conversation (outside global lock — constructor may do I/O)
    conv_id: uuid.UUID | None = None
    if session_id:
        try:
            conv_id = uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid session_id: {session_id}")

    conv = Conversation(
        agent=dash,
        workspace=".",
        persistence_dir=str(PERSISTENCE_DIR),
        conversation_id=conv_id,
    )

    if ENABLE_CONFIRMATION:
        conv.set_confirmation_policy(confirmation_policy)

    sid = str(getattr(conv, "conversation_id", session_id or uuid.uuid4()))
    entry = _SessionEntry(conv)

    with _sessions_lock:
        _sessions[sid] = entry

    return entry, sid


# ============================================================================
# Lifespan — graceful shutdown
# ============================================================================


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    # Shutdown: close all conversations so tool executors are cleaned up
    logger.info("Shutting down — closing %d session(s)", len(_sessions))
    _close_all_sessions()


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Dash",
    description="A self-learning data agent that provides insights, not just query results.",
    version="1.0.0",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


class SessionInfo(BaseModel):
    session_id: str
    persistence_dir: str


# ============================================================================
# Endpoints
# ============================================================================


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to Dash and get a response."""
    entry, sid = _get_or_create_session(request.session_id)

    def _run_sync() -> str:
        entry.acquire_flight()
        try:
            # Per-session lock serialises concurrent requests to the same session
            with entry.lock:
                entry.touch()
                entry.conversation.send_message(request.message)
                entry.conversation.run()
                return get_agent_final_response(entry.conversation.state.events)
        finally:
            entry.release_flight()

    try:
        response_text = await asyncio.wait_for(
            asyncio.to_thread(_run_sync),
            timeout=CHAT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Agent did not respond within {CHAT_TIMEOUT_SECONDS}s",
        )

    return ChatResponse(response=response_text, session_id=sid)


@app.post("/sessions", response_model=SessionInfo)
async def create_session() -> SessionInfo:
    """Create a new conversation session."""
    _, sid = _get_or_create_session(None)
    return SessionInfo(session_id=sid, persistence_dir=str(PERSISTENCE_DIR))


@app.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str) -> SessionInfo:
    """Check if a session exists."""
    with _sessions_lock:
        in_memory = session_id in _sessions

    if not in_memory:
        try:
            conv_id = uuid.UUID(session_id)
            persist_path = Conversation.get_persistence_dir(str(PERSISTENCE_DIR), conv_id)
            if not Path(persist_path).exists():
                raise HTTPException(status_code=404, detail="Session not found")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session_id")

    return SessionInfo(session_id=session_id, persistence_dir=str(PERSISTENCE_DIR))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(getenv("PORT", "7777")),
        reload=getenv("RUNTIME_ENV", "prd") == "dev",
    )
