#!/usr/bin/env python3
"""
Cloud API Demo — Programmatic Data Workflows with OpenHands
============================================================

Shows how to start an OpenHands conversation via the REST API and run a
data task (e.g., a data quality audit or a KPI check).  This works with
both a self-hosted OpenHands server and OpenHands Cloud.

Usage:
    # Self-hosted (default: http://localhost:3000)
    python scripts/cloud_api_demo.py

    # OpenHands Cloud
    OPENHANDS_HOST=https://app.openhands.ai \
    OPENHANDS_API_KEY=oh-... \
    python scripts/cloud_api_demo.py

    # Custom question
    python scripts/cloud_api_demo.py "Compare Ferrari vs Mercedes points 2015-2020"

Environment variables:
    OPENHANDS_HOST     Base URL of the OpenHands server (default: http://localhost:3000)
    OPENHANDS_API_KEY  API key — required for OpenHands Cloud, optional for self-hosted

Reference:
    https://docs.openhands.dev/openhands/usage/cloud/cloud-api
"""

import json
import os
import sys
import time

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HOST = os.getenv("OPENHANDS_HOST", "http://localhost:3000").rstrip("/")
API_KEY = os.getenv("OPENHANDS_API_KEY", "")

DEFAULT_QUESTION = "Run a data quality audit: check for NULL counts, duplicate rows, and type mismatches across all tables."

HEADERS: dict[str, str] = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["Authorization"] = f"Bearer {API_KEY}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def api(method: str, path: str, **kwargs) -> httpx.Response:
    """Make an API request and raise on error."""
    url = f"{HOST}{path}"
    resp = httpx.request(method, url, headers=HEADERS, timeout=120, **kwargs)
    resp.raise_for_status()
    return resp


def create_conversation() -> str:
    """Create a new conversation and return its ID."""
    resp = api("POST", "/api/conversations", json={})
    data = resp.json()
    conv_id = data.get("conversation_id") or data.get("id")
    print(f"✅ Created conversation: {conv_id}")
    return conv_id


def send_message(conv_id: str, message: str) -> None:
    """Send a user message to the conversation."""
    api(
        "POST",
        f"/api/conversations/{conv_id}/messages",
        json={"role": "user", "content": message},
    )
    print(f"📤 Sent: {message[:80]}{'…' if len(message) > 80 else ''}")


def poll_until_done(conv_id: str, timeout: int = 300, interval: int = 3) -> list[dict]:
    """Poll for new events until the agent finishes or times out."""
    start = time.monotonic()
    seen = 0
    all_events: list[dict] = []

    while time.monotonic() - start < timeout:
        resp = api("GET", f"/api/conversations/{conv_id}/events")
        events = resp.json()

        for event in events[seen:]:
            all_events.append(event)
            _print_event(event)
        seen = len(events)

        # Check if the agent has finished
        if any(_is_finish(e) for e in events[seen - len(all_events):]):
            return all_events

        time.sleep(interval)

    print(f"⏰ Timed out after {timeout}s")
    return all_events


def _is_finish(event: dict) -> bool:
    """Check if an event indicates the agent is done."""
    action = event.get("action", {})
    return action.get("action_type") in ("finish", "AgentFinishAction")


def _print_event(event: dict) -> None:
    """Pretty-print a conversation event."""
    action = event.get("action", {})
    observation = event.get("observation", {})

    action_type = action.get("action_type", "")
    obs_type = observation.get("observation_type", "")

    if action_type == "message" and action.get("role") == "assistant":
        content = action.get("content", "")
        print(f"\n💬 Assistant:\n{content}\n")
    elif action_type in ("run", "CmdRunAction"):
        cmd = action.get("command", "")
        print(f"  🖥️  Running: {cmd}")
    elif obs_type in ("run", "CmdOutputObservation"):
        output = observation.get("content", "")[:500]
        if output.strip():
            print(f"  📋 Output: {output}")
    elif action_type in ("finish", "AgentFinishAction"):
        thought = action.get("thought", "")
        print(f"\n✅ Agent finished: {thought[:200]}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    question = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUESTION

    print("=" * 60)
    print("  Dash — Cloud API Demo")
    print("=" * 60)
    print(f"  Server:   {HOST}")
    print(f"  API Key:  {'***' + API_KEY[-4:] if API_KEY else '(none — self-hosted)'}")
    print()

    # 1. Create conversation
    conv_id = create_conversation()

    # 2. Send the question
    send_message(conv_id, question)

    # 3. Poll for events until the agent finishes
    print("\n⏳ Waiting for agent…\n")
    events = poll_until_done(conv_id)

    # 4. Summary
    print("\n" + "=" * 60)
    print(f"  Conversation: {conv_id}")
    print(f"  Events:       {len(events)}")
    print(f"  View in UI:   {HOST}/conversations/{conv_id}")
    print("=" * 60)


if __name__ == "__main__":
    main()
