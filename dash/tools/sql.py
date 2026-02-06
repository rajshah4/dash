"""SQL execution tool for running queries against the database."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from pydantic import Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError, OperationalError

from openhands.sdk.tool.schema import Action, Observation
from openhands.sdk.tool.tool import ToolAnnotations, ToolDefinition, ToolExecutor


if TYPE_CHECKING:
    from openhands.sdk.conversation import LocalConversation
    from openhands.sdk.conversation.state import ConversationState


# ============================================================================
# Action / Observation schemas
# ============================================================================


class RunSQLAction(Action):
    """Execute a read-only SQL query against the database."""

    query: str = Field(description="The SQL query to execute. Must be a SELECT or WITH statement.")
    limit: int = Field(default=50, description="Maximum number of rows to return.")


class RunSQLObservation(Observation):
    """Result of a SQL query execution."""

    pass


# ============================================================================
# Executor
# ============================================================================

DANGEROUS_KEYWORDS = ["drop", "delete", "truncate", "insert", "update", "alter", "create"]


class RunSQLExecutor(ToolExecutor[RunSQLAction, RunSQLObservation]):
    """Execute SQL queries against a database."""

    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(db_url)

    def __call__(
        self, action: RunSQLAction, conversation: "LocalConversation | None" = None
    ) -> RunSQLObservation:
        query = action.query.strip().rstrip(";")
        sql_lower = query.lower()

        # Safety checks
        if not sql_lower.startswith(("select", "with")):
            return RunSQLObservation.from_text("Error: Only SELECT / WITH queries are allowed.", is_error=True)

        for kw in DANGEROUS_KEYWORDS:
            if f" {kw} " in f" {sql_lower} ":
                return RunSQLObservation.from_text(f"Error: Query contains dangerous keyword: {kw}", is_error=True)

        # Ensure LIMIT — cap at action.limit even if user already has a higher one
        if "limit" not in sql_lower:
            query = f"{query}\nLIMIT {action.limit}"

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                columns = list(result.keys())
                rows = result.fetchall()

            if not rows:
                return RunSQLObservation.from_text("Query returned no results.")

            # Format as markdown table
            lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
            for row in rows:
                vals = [str(v)[:50] if v is not None else "NULL" for v in row]
                lines.append("| " + " | ".join(vals) + " |")

            lines.append(f"\n_{len(rows)} row(s) returned_")
            return RunSQLObservation.from_text("\n".join(lines))

        except (OperationalError, DatabaseError) as e:
            return RunSQLObservation.from_text(f"SQL Error: {e}", is_error=True)
        except Exception as e:
            return RunSQLObservation.from_text(f"Error: {e}", is_error=True)

    def close(self) -> None:
        self.engine.dispose()


# ============================================================================
# Tool Definition
# ============================================================================


TOOL_DESCRIPTION = """\
Execute a read-only SQL query against the PostgreSQL database.

Use this tool to query the F1 data tables. Rules:
- Only SELECT or WITH (CTE) queries are allowed
- No DROP, DELETE, UPDATE, INSERT, ALTER, or CREATE
- Results are limited to 50 rows by default
- Always specify column names (avoid SELECT *)
- Use ORDER BY for top-N / ranking queries
"""


class RunSQLTool(ToolDefinition[RunSQLAction, RunSQLObservation]):
    """SQL query execution tool."""

    @classmethod
    def create(
        cls,
        conv_state: "ConversationState | None" = None,
        db_url: str = "",
        **kwargs: Any,
    ) -> Sequence["RunSQLTool"]:
        if not db_url:
            raise ValueError("db_url is required for RunSQLTool")
        return [
            cls(
                description=TOOL_DESCRIPTION,
                action_type=RunSQLAction,
                observation_type=RunSQLObservation,
                annotations=ToolAnnotations(
                    title="run_sql",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=RunSQLExecutor(db_url),
            )
        ]
