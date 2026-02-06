"""CLI entry point: python -m dash"""

import argparse
import sys
import uuid
from pathlib import Path

from openhands.sdk import Conversation

from dash.agents import confirmation_policy, dash
from dash.paths import PROJECT_ROOT

# Default persistence directory for conversation history
PERSISTENCE_DIR = PROJECT_ROOT / ".dash_sessions"


def main() -> None:
    """Run Dash in interactive CLI mode."""
    parser = argparse.ArgumentParser(description="Dash — Self-learning F1 data agent")
    parser.add_argument("question", nargs="*", help="Question to ask (one-shot mode)")
    parser.add_argument(
        "--session", "-s",
        type=str,
        default=None,
        help="Resume a previous session by ID",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Disable conversation persistence",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Enable confirmation prompts for risky actions",
    )
    args = parser.parse_args()

    # Persistence setup
    persist_dir: Path | None = None if args.no_persist else PERSISTENCE_DIR
    conversation_id: uuid.UUID | None = None

    if args.session:
        try:
            conversation_id = uuid.UUID(args.session)
        except ValueError:
            print(f"Invalid session ID: {args.session}")
            sys.exit(1)

    # Create conversation with persistence
    conv_kwargs: dict = {"agent": dash, "workspace": "."}
    if persist_dir:
        conv_kwargs["persistence_dir"] = str(persist_dir)
    if conversation_id:
        conv_kwargs["conversation_id"] = conversation_id

    conversation = Conversation(**conv_kwargs)

    # Apply security confirmation policy if requested
    if args.confirm:
        conversation.set_confirmation_policy(confirmation_policy)

    # Print session info
    if persist_dir and not args.question:
        session_id = getattr(conversation, "conversation_id", None)
        if session_id:
            print(f"Session: {session_id}")
            print(f"Resume with: python -m dash --session {session_id}\n")

    if args.question:
        # One-shot mode
        message = " ".join(args.question)
        conversation.send_message(message)
        conversation.run()
    else:
        # Interactive mode
        print("🏎️  Dash — Self-learning F1 data agent")
        print("Type your question (or 'quit' to exit):\n")
        while True:
            try:
                question = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break
            if not question or question.lower() in ("quit", "exit", "q"):
                print("Bye!")
                break
            conversation.send_message(question)
            conversation.run()
            print()

    conversation.close()


if __name__ == "__main__":
    main()
