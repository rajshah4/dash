"""
Dash Platform Mode
==================

Run Dash on the full OpenHands platform via RemoteConversation.

This connects to a running OpenHands server and provides:
  - Sandboxed bash terminal (psql, Python scripts, etc.)
  - File editor (browse/edit knowledge, save reports)
  - Browser (preview visualizations)
  - Plus all custom SQL tools (run_sql, introspect_schema, save_validated_query)

Usage:
    # 1. Start the OpenHands server (see compose.platform.yaml)
    docker compose -f compose.platform.yaml up -d

    # 2. Connect Dash to the platform
    python -m dash.platform

    # Or use environment variables to configure:
    OPENHANDS_HOST=http://localhost:3000 python -m dash.platform

Environment variables:
    OPENHANDS_HOST       OpenHands server URL (default: http://localhost:3000)
    OPENHANDS_API_KEY    API key for the OpenHands server (optional)
"""

from os import getenv

from openhands.sdk.conversation.impl.remote_conversation import RemoteConversation
from openhands.sdk.conversation.response_utils import get_agent_final_response
from openhands.sdk.logger import get_logger
from openhands.sdk.workspace.remote.base import RemoteWorkspace

from dash.agents import confirmation_policy, dash_platform

logger = get_logger(__name__)

OPENHANDS_HOST = getenv("OPENHANDS_HOST", "http://localhost:3000")
OPENHANDS_API_KEY = getenv("OPENHANDS_API_KEY")


def main() -> None:
    """Interactive CLI for Dash running on the OpenHands platform."""
    print("━" * 60)
    print("  Dash (Platform Mode)")
    print(f"  Connected to: {OPENHANDS_HOST}")
    print("  Type 'quit' or 'exit' to stop.")
    print("━" * 60)
    print()

    workspace = RemoteWorkspace(
        host=OPENHANDS_HOST,
        working_dir="/workspace",
        api_key=OPENHANDS_API_KEY,
    )

    conversation = RemoteConversation(
        agent=dash_platform,
        workspace=workspace,
    )
    conversation.set_confirmation_policy(confirmation_policy)

    try:
        while True:
            try:
                question = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not question:
                continue
            if question.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            conversation.send_message(question)
            conversation.run()
            response = get_agent_final_response(conversation.state.events)
            print(f"\nDash: {response}\n")
    finally:
        try:
            conversation.close()
        except Exception:
            logger.warning("Error closing conversation", exc_info=True)


if __name__ == "__main__":
    main()
