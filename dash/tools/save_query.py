"""Save validated SQL queries tool."""

from __future__ import annotations

import json
import logging
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

    name: str = Field(description='Short name for the query (e.g., "championship_wins_by_driver")')
    question: str = Field(description="The original user question this query answers")
    query: str = Field(description="The validated SQL query")
    summary: str | None = Field(default=None, description="Brief description of what the query does")
    tables_used: list[str] | None = Field(default=None, description="List of tables used in the query")
    data_quality_notes: str | None = Field(default=None, description="Any data quality issues handled")


class SaveValidatedQueryObservation(Observation):
    """Result of saving a validated query."""

    pass


# ============================================================================
# Executor
# ============================================================================

DANGEROUS_KEYWORDS = ["drop", "delete", "truncate", "insert", "update", "alter", "create"]


class SaveValidatedQueryExecutor(ToolExecutor[SaveValidatedQueryAction, SaveValidatedQueryObservation]):
    """Save validated queries to a local JSON file."""

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

        payload: dict[str, Any] = {
            "type": "validated_query",
            "name": action.name.strip(),
            "question": action.question.strip(),
            "query": action.query.strip(),
        }
        if action.summary:
            payload["summary"] = action.summary.strip()
        if action.tables_used:
            payload["tables_used"] = action.tables_used
        if action.data_quality_notes:
            payload["data_quality_notes"] = action.data_quality_notes.strip()

        try:
            filename = action.name.strip().replace(" ", "_").lower() + ".json"
            filepath = self.queries_dir / filename
            if filepath.exists():
                return SaveValidatedQueryObservation.from_text(
                    f"Query '{action.name}' already exists. Skipped."
                )
            with open(filepath, "w") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return SaveValidatedQueryObservation.from_text(f"Saved query '{action.name}' to {filepath}.")
        except OSError as e:
            logger.error(f"Failed to save query: {e}")
            return SaveValidatedQueryObservation.from_text(f"Error: {e}", is_error=True)

    def close(self) -> None:
        pass


# ============================================================================
# Tool Definition
# ============================================================================


TOOL_DESCRIPTION = """\
Save a validated SQL query to the knowledge base for future reuse.

Call ONLY after the query has executed successfully and the user confirmed results are correct.
Saved queries will be available in the knowledge directory for future reference.
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
