"""Save validated SQL queries tool (Layer 3).

Saves queries in the same tagged .sql format as curated patterns so they
are loaded back into the prompt for future sessions.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import Field

from openhands.sdk.tool.schema import Action, Observation
from openhands.sdk.tool.tool import ToolAnnotations, ToolDefinition, ToolExecutor


if TYPE_CHECKING:
    from openhands.sdk.conversation import LocalConversation
    from openhands.sdk.conversation.state import ConversationState

logger = logging.getLogger(__name__)


# ============================================================================
# Action / Observation schemas
# ============================================================================


class SaveValidatedQueryAction(Action):
    """Save a validated SQL query for future reference."""

    name: str = Field(description='Short snake_case name for the query (e.g., "championship_wins_by_driver")')
    question: str = Field(description="The original user question this query answers")
    query: str = Field(description="The validated SQL query")
    description: str | None = Field(default=None, description="What the query does, gotchas it handles")
    tables_used: list[str] | None = Field(default=None, description="List of tables used in the query")


class SaveValidatedQueryObservation(Observation):
    """Result of saving a validated query."""

    pass


# ============================================================================
# Executor
# ============================================================================

DANGEROUS_KEYWORDS = ["drop", "delete", "truncate", "insert", "update", "alter", "create"]


class SaveValidatedQueryExecutor(ToolExecutor[SaveValidatedQueryAction, SaveValidatedQueryObservation]):
    """Save validated queries as .sql files matching the curated format."""

    def __init__(self, queries_dir: Path) -> None:
        self.queries_dir = queries_dir
        self.queries_dir.mkdir(parents=True, exist_ok=True)

    def __call__(
        self,
        action: SaveValidatedQueryAction,
        conversation: "LocalConversation | None" = None,
    ) -> SaveValidatedQueryObservation:
        if not action.name or not action.name.strip():
            return SaveValidatedQueryObservation.from_text("Error: Name required.", is_error=True)
        if not action.question or not action.question.strip():
            return SaveValidatedQueryObservation.from_text("Error: Question required.", is_error=True)
        if not action.query or not action.query.strip():
            return SaveValidatedQueryObservation.from_text("Error: Query required.", is_error=True)

        sql = action.query.strip().lower()
        if not sql.startswith("select") and not sql.startswith("with"):
            return SaveValidatedQueryObservation.from_text("Error: Only SELECT queries can be saved.", is_error=True)

        for kw in DANGEROUS_KEYWORDS:
            if f" {kw} " in f" {sql} ":
                return SaveValidatedQueryObservation.from_text(
                    f"Error: Query contains dangerous keyword: {kw}", is_error=True
                )

        # Sanitize name to snake_case
        name = re.sub(r"[^a-z0-9_]", "_", action.name.strip().lower())
        name = re.sub(r"_+", "_", name).strip("_")
        if not name:
            return SaveValidatedQueryObservation.from_text("Error: Invalid name.", is_error=True)

        # Check if a query with this name already exists in any .sql file
        if self._query_exists(name):
            return SaveValidatedQueryObservation.from_text(
                f"Query '{name}' already exists. Skipped."
            )

        # Build the tagged SQL format matching knowledge/queries/*.sql
        desc_text = action.description or action.question
        desc_lines = "\n".join(f"-- {line}" for line in desc_text.strip().splitlines())
        if action.tables_used:
            desc_lines += f"\n-- Tables: {', '.join(action.tables_used)}"

        content = (
            f"\n\n-- <query name>{name}</query name>\n"
            f"-- <query description>\n"
            f"{desc_lines}\n"
            f"-- </query description>\n"
            f"-- <query>\n"
            f"{action.query.strip()}\n"
            f"-- </query>\n"
        )

        try:
            # Append to a saved_queries.sql file (keeps all saved queries together)
            filepath = self.queries_dir / "saved_queries.sql"
            with open(filepath, "a") as f:
                f.write(content)
            return SaveValidatedQueryObservation.from_text(
                f"Saved query '{name}' to {filepath}.\n"
                f"This query will be available as a pattern in future sessions."
            )
        except OSError as e:
            logger.error(f"Failed to save query: {e}")
            return SaveValidatedQueryObservation.from_text(f"Error: {e}", is_error=True)

    def _query_exists(self, name: str) -> bool:
        """Check if a query with this name already exists in any .sql file."""
        pattern = re.compile(rf"<query name>\s*{re.escape(name)}\s*</query name>")
        for filepath in self.queries_dir.glob("*.sql"):
            try:
                content = filepath.read_text()
                if pattern.search(content):
                    return True
            except OSError:
                pass
        return False

    def close(self) -> None:
        pass


# ============================================================================
# Tool Definition
# ============================================================================


TOOL_DESCRIPTION = """\
Save a validated SQL query to the knowledge base for future reuse.

Call ONLY after the query has executed successfully and the user confirmed
results are correct. Saved queries become patterns that future sessions can
reference — they are loaded into the system prompt automatically.

Parameters:
- name: Short snake_case name (e.g., "driver_wins_by_year")
- question: The original user question
- query: The validated SQL
- description: What it does and any gotchas handled
- tables_used: Tables referenced in the query
"""


class SaveValidatedQueryTool(ToolDefinition[SaveValidatedQueryAction, SaveValidatedQueryObservation]):
    """Save validated queries to knowledge base."""

    @classmethod
    def create(
        cls,
        conv_state: "ConversationState | None" = None,
        queries_dir: str = "",
        **kwargs: Any,
    ) -> Sequence["SaveValidatedQueryTool"]:
        if not queries_dir:
            raise ValueError("queries_dir is required for SaveValidatedQueryTool")
        return [
            cls(
                description=TOOL_DESCRIPTION,
                action_type=SaveValidatedQueryAction,
                observation_type=SaveValidatedQueryObservation,
                annotations=ToolAnnotations(
                    title="save_validated_query",
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=SaveValidatedQueryExecutor(Path(queries_dir)),
            )
        ]
