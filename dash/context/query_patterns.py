"""Load validated SQL query patterns for the system prompt (Layer 3)."""

import logging
import re
from pathlib import Path

from dash.paths import QUERIES_DIR

logger = logging.getLogger(__name__)

# Regex to parse the tagged SQL format used in knowledge/queries/*.sql
_QUERY_PATTERN = re.compile(
    r"--\s*<query name>\s*(.+?)\s*</query name>\s*\n"
    r"--\s*<query description>\s*\n(.*?)--\s*</query description>\s*\n"
    r"--\s*<query>\s*\n(.*?)--\s*</query>",
    re.DOTALL,
)


def load_query_patterns(queries_dir: Path | None = None) -> list[dict[str, str]]:
    """Load validated query patterns from .sql files."""
    if queries_dir is None:
        queries_dir = QUERIES_DIR

    patterns: list[dict[str, str]] = []
    if not queries_dir.exists():
        return patterns

    for filepath in sorted(queries_dir.glob("*.sql")):
        try:
            content = filepath.read_text()
            for match in _QUERY_PATTERN.finditer(content):
                name = match.group(1).strip()
                # Strip leading "-- " from each description line
                desc_raw = match.group(2)
                desc = "\n".join(
                    line.lstrip("-").strip() for line in desc_raw.strip().splitlines()
                ).strip()
                sql = match.group(3).strip()
                patterns.append({"name": name, "description": desc, "sql": sql})
        except OSError as e:
            logger.error(f"Failed to load {filepath}: {e}")

    return patterns


def build_query_patterns_context(queries_dir: Path | None = None) -> str:
    """Build query patterns string for the system prompt."""
    patterns = load_query_patterns(queries_dir)
    if not patterns:
        return ""

    lines = ["## VALIDATED QUERY PATTERNS\n"]
    lines.append("These queries are known to work. Use them as templates.\n")

    for p in patterns:
        lines.append(f"### {p['name']}")
        if p["description"]:
            lines.append(p["description"])
        lines.append(f"```sql\n{p['sql']}\n```")
        lines.append("")

    return "\n".join(lines)


QUERY_PATTERNS_CONTEXT = build_query_patterns_context()
