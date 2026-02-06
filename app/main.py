"""
Dash API
========

Production deployment entry point for Dash.
Provides a FastAPI server with /chat, /sessions, and /health endpoints.

Features:
- Persistent conversations (saved to disk, resumable by session_id)
- Security confirmation policy (optional)
- LRU session eviction to bound memory usage

Run:
    python -m app.main
"""

import asyncio
import threading
import time
import uuid
from collections import OrderedDict
from os import getenv
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from openhands.sdk import Conversation
from openhands.sdk.conversation.response_utils import get_agent_final_response

from dash.agents import confirmation_policy, dash
from dash.paths import PROJECT_ROOT

# ============================================================================
# Configuration
# ============================================================================

PERSISTENCE_DIR = Path(getenv("DASH_PERSISTENCE_DIR", str(PROJECT_ROOT / ".dash_sessions")))
ENABLE_CONFIRMATION = getenv("DASH_ENABLE_CONFIRMATION", "false").lower() == "true"
MAX_SESSIONS = int(getenv("DASH_MAX_SESSIONS", "100"))
SESSION_TTL_SECONDS = int(getenv("DASH_SESSION_TTL", str(60 * 60)))  # 1 hour default

# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Dash",
    description="A self-learning data agent that provides insights, not just query results.",
    version="1.0.0",
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
# Session management with persistence + LRU eviction
# ============================================================================

_sessions: OrderedDict[str, tuple[Conversation, float]] = OrderedDict()
_sessions_lock = threading.Lock()


def _evict_stale_sessions() -> None:
    """Remove sessions that exceed TTL or the max count (LRU)."""
    now = time.monotonic()
    with _sessions_lock:
        # Evict expired sessions
        expired = [sid for sid, (_, ts) in _sessions.items() if now - ts > SESSION_TTL_SECONDS]
        for sid in expired:
            conv, _ = _sessions.pop(sid)
            try:
                conv.close()
            except Exception:
                pass

        # Evict oldest if over capacity
        while len(_sessions) > MAX_SESSIONS:
            _, (conv, _) = _sessions.popitem(last=False)
            try:
                conv.close()
            except Exception:
                pass


def _get_or_create_conversation(session_id: str | None) -> tuple[Conversation, str]:
    """Get an existing conversation or create a new one with persistence."""
    _evict_stale_sessions()

    with _sessions_lock:
        # Resume existing in-memory session
        if session_id and session_id in _sessions:
            conv, _ = _sessions[session_id]
            _sessions.move_to_end(session_id)  # refresh LRU position
            _sessions[session_id] = (conv, time.monotonic())
            return conv, session_id

    # Try to resume from disk
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

    with _sessions_lock:
        _sessions[sid] = (conv, time.monotonic())

    return conv, sid


# ============================================================================
# Endpoints
# ============================================================================


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message to Dash and get a response."""
    conversation, sid = _get_or_create_conversation(request.session_id)

    def _run_sync() -> str:
        conversation.send_message(request.message)
        conversation.run()
        return get_agent_final_response(conversation.state.events)

    response_text = await asyncio.to_thread(_run_sync)
    return ChatResponse(response=response_text, session_id=sid)


@app.post("/sessions", response_model=SessionInfo)
async def create_session() -> SessionInfo:
    """Create a new conversation session."""
    _, sid = _get_or_create_conversation(None)
    return SessionInfo(session_id=sid, persistence_dir=str(PERSISTENCE_DIR))


@app.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str) -> SessionInfo:
    """Check if a session exists."""
    with _sessions_lock:
        in_memory = session_id in _sessions

    if not in_memory:
        # Check if it exists on disk
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
