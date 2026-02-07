"""Load persistent learnings for the system prompt (Layer 5).

Learnings are discoveries the agent makes during sessions — schema quirks,
type gotchas, error patterns, data quality issues. They survive across
sessions so the agent never re-discovers the same thing twice.
"""

import json
import logging
from pathlib import Path
from typing import Any

from dash.paths import LEARNINGS_DIR

logger = logging.getLogger(__name__)


def load_learnings(learnings_dir: Path | None = None) -> list[dict[str, Any]]:
    """Load learnings from JSON files."""
    if learnings_dir is None:
        learnings_dir = LEARNINGS_DIR

    learnings: list[dict[str, Any]] = []
    if not learnings_dir.exists():
        return learnings

    for filepath in sorted(learnings_dir.glob("*.json")):
        try:
            with open(filepath) as f:
                data = json.load(f)
            # Support both single-learning files and lists
            if isinstance(data, list):
                learnings.extend(data)
            elif isinstance(data, dict):
                learnings.append(data)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load {filepath}: {e}")

    return learnings


def build_learnings_context(learnings_dir: Path | None = None) -> str:
    """Build learnings string for the system prompt."""
    learnings = load_learnings(learnings_dir)
    if not learnings:
        return ""

    lines = ["## LEARNINGS FROM PREVIOUS SESSIONS\n"]
    lines.append("These patterns were discovered in earlier sessions. Apply them.\n")

    for lr in learnings:
        category = lr.get("category", "general")
        description = lr.get("description", "")
        tables = lr.get("tables_affected", [])
        example = lr.get("example", "")

        icon = {
            "schema_quirk": "⚠️",
            "type_gotcha": "🔢",
            "error_fix": "🔧",
            "data_pattern": "📊",
            "performance": "⚡",
        }.get(category, "💡")

        lines.append(f"- {icon} **{category}**: {description}")
        if tables:
            lines.append(f"  - Tables: {', '.join(tables)}")
        if example:
            lines.append(f"  - Example: `{example}`")

    lines.append("")
    return "\n".join(lines)


LEARNINGS_CONTEXT = build_learnings_context()
