"""
Dash Platform Mode
==================

Starts the OpenHands platform with Dash's context injected.

The OpenHands agent (CodeAct) gets Dash's 6 layers of context via the
.openhands_instructions file in the workspace root. This turns the general
coding agent into a data-specialized agent that knows:

  - The database schema and connection details
  - Critical data quality gotchas (position TEXT vs INTEGER, date formats)
  - Validated SQL patterns that are known to work
  - Business rules and metric definitions
  - Learnings from previous sessions

The agent uses the platform's built-in tools:
  - bash (psql, Python scripts, data analysis)
  - file editor (browse/edit knowledge files)
  - browser (preview visualizations)

Usage:
  # Start the platform
  docker compose -f compose.platform.yaml up -d

  # Open the web UI
  python -m dash.platform

  # Or just open http://localhost:3000 directly
"""

import os
import subprocess
import sys
import webbrowser


OPENHANDS_URL = os.getenv("OPENHANDS_SERVER_URL", "http://localhost:3000")


def main() -> None:
    """Launch the OpenHands platform for Dash."""
    print("=" * 60)
    print("  Dash — Platform Mode")
    print("=" * 60)
    print()
    print("The OpenHands platform extends Dash with:")
    print("  🖥️  Terminal — psql, Python scripts, data analysis")
    print("  📝  File Editor — browse/edit knowledge files")
    print("  🌐  Browser — preview visualizations")
    print("  🔒  Sandbox — isolated Docker runtime")
    print()

    # Check if the platform is running
    try:
        import httpx

        resp = httpx.get(OPENHANDS_URL, timeout=3, follow_redirects=True)
        if resp.status_code == 200:
            print(f"✅ OpenHands is running at {OPENHANDS_URL}")
            print()
            print("Opening in your browser...")
            webbrowser.open(OPENHANDS_URL)
            return
    except Exception:
        pass

    # Not running — offer to start it
    print(f"❌ OpenHands is not running at {OPENHANDS_URL}")
    print()
    print("Start it with:")
    print()
    print("  docker compose -f compose.platform.yaml up -d")
    print()

    if "--start" in sys.argv:
        print("Starting...")
        result = subprocess.run(
            ["docker", "compose", "-f", "compose.platform.yaml", "up", "-d"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        if result.returncode == 0:
            print()
            print(f"✅ Platform started! Opening {OPENHANDS_URL}")
            webbrowser.open(OPENHANDS_URL)
        else:
            print("❌ Failed to start. Check Docker is running.")
            sys.exit(1)


if __name__ == "__main__":
    main()
