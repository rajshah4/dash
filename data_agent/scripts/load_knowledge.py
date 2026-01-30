"""
Load Knowledge
==============

Loads table metadata, query patterns, and business definitions into
the Data Agent's knowledge base.

Usage:
    python -m data_agent.scripts.load_knowledge

This script loads all files from the knowledge/ directory:
- knowledge/tables/*.json - Table metadata with data quality notes
- knowledge/queries/*.sql - Validated query patterns
- knowledge/business/*.json - Business definitions and rules
"""

import sys
from pathlib import Path

# Knowledge directory
KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


def load_knowledge(verbose: bool = True) -> bool:
    """Load knowledge files into the Data Agent's knowledge base.

    Args:
        verbose: Print progress messages.

    Returns:
        True if knowledge loaded successfully, False otherwise.
    """
    # Import here to avoid circular imports
    from data_agent.agent import data_agent_knowledge

    try:
        if verbose:
            print("Loading knowledge from:", KNOWLEDGE_DIR)
            print()

        # Load all subdirectories
        subdirs = ["tables", "queries", "business"]
        for subdir in subdirs:
            subdir_path = KNOWLEDGE_DIR / subdir
            if subdir_path.exists():
                files = list(subdir_path.glob("*"))
                if verbose:
                    print(f"Loading {subdir}/ ({len(files)} files)...")

                data_agent_knowledge.insert(
                    name=f"Data Agent Knowledge - {subdir}",
                    path=str(subdir_path),
                )

                if verbose:
                    for f in files:
                        print(f"  - {f.name}")

        if verbose:
            print()
            print("Knowledge loaded successfully!")

        return True

    except Exception as e:
        if verbose:
            print(f"Failed to load knowledge: {e}")
        return False


def main() -> int:
    """Main entry point."""
    print("Loading knowledge into Data Agent knowledge base...")
    print()

    success = load_knowledge(verbose=True)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
