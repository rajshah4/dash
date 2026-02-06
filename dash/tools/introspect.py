"""Runtime schema inspection tool (Layer 6)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from pydantic import Field
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DatabaseError, OperationalError

from openhands.sdk.tool.schema import Action, Observation
from openhands.sdk.tool.tool import ToolAnnotations, ToolDefinition, ToolExecutor


if TYPE_CHECKING:
    from openhands.sdk.conversation import LocalConversation
    from openhands.sdk.conversation.state import ConversationState


# ============================================================================
# Action / Observation schemas
# ============================================================================


class IntrospectSchemaAction(Action):
    """Inspect the database schema at runtime."""

    table_name: str | None = Field(default=None, description="Table to inspect. If None, lists all tables.")
    include_sample_data: bool = Field(default=False, description="Include sample rows from the table.")
    sample_limit: int = Field(default=5, description="Number of sample rows to return.")


class IntrospectSchemaObservation(Observation):
    """Result of a schema introspection."""

    pass


# ============================================================================
# Executor
# ============================================================================


class IntrospectSchemaExecutor(ToolExecutor[IntrospectSchemaAction, IntrospectSchemaObservation]):
    """Inspect database schema at runtime."""

    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(db_url)

    def __call__(
        self,
        action: IntrospectSchemaAction,
        conversation: "LocalConversation | None" = None,
    ) -> IntrospectSchemaObservation:
        try:
            insp = inspect(self.engine)

            if action.table_name is None:
                # List all tables
                tables = insp.get_table_names()
                if not tables:
                    return IntrospectSchemaObservation.from_text("No tables found.")

                lines = ["## Tables", ""]
                for t in sorted(tables):
                    try:
                        with self.engine.connect() as conn:
                            count = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
                            lines.append(f"- **{t}** ({count:,} rows)")
                    except (OperationalError, DatabaseError):
                        lines.append(f"- **{t}**")
                return IntrospectSchemaObservation.from_text("\n".join(lines))

            # Inspect specific table
            tables = insp.get_table_names()
            if action.table_name not in tables:
                return IntrospectSchemaObservation.from_text(
                    f"Table '{action.table_name}' not found. Available: {', '.join(sorted(tables))}",
                    is_error=True,
                )

            lines = [f"## {action.table_name}", ""]

            # Columns
            cols = insp.get_columns(action.table_name)
            if cols:
                lines.extend(["### Columns", "", "| Column | Type | Nullable |", "| --- | --- | --- |"])
                for c in cols:
                    nullable = "Yes" if c.get("nullable", True) else "No"
                    lines.append(f"| {c['name']} | {c['type']} | {nullable} |")
                lines.append("")

            # Primary key
            pk = insp.get_pk_constraint(action.table_name)
            if pk and pk.get("constrained_columns"):
                lines.append(f"**Primary Key:** {', '.join(pk['constrained_columns'])}")
                lines.append("")

            # Sample data
            if action.include_sample_data:
                lines.append("### Sample")
                try:
                    with self.engine.connect() as conn:
                        result = conn.execute(
                            text(f'SELECT * FROM "{action.table_name}" LIMIT {action.sample_limit}')
                        )
                        rows = result.fetchall()
                        col_names = list(result.keys())
                        if rows:
                            lines.append("| " + " | ".join(col_names) + " |")
                            lines.append("| " + " | ".join(["---"] * len(col_names)) + " |")
                            for row in rows:
                                vals = [str(v)[:30] if v else "NULL" for v in row]
                                lines.append("| " + " | ".join(vals) + " |")
                        else:
                            lines.append("_No data_")
                except (OperationalError, DatabaseError) as e:
                    lines.append(f"_Error: {e}_")

            return IntrospectSchemaObservation.from_text("\n".join(lines))

        except OperationalError as e:
            return IntrospectSchemaObservation.from_text(f"Error: Database connection failed - {e}", is_error=True)
        except DatabaseError as e:
            return IntrospectSchemaObservation.from_text(f"Error: {e}", is_error=True)

    def close(self) -> None:
        self.engine.dispose()


# ============================================================================
# Tool Definition
# ============================================================================


TOOL_DESCRIPTION = """\
Inspect the database schema at runtime.

Use this to discover tables, columns, types, and sample data.
- Call with no arguments to list all tables
- Call with table_name to see columns and types
- Set include_sample_data=true to see sample rows
"""


class IntrospectSchemaTool(ToolDefinition[IntrospectSchemaAction, IntrospectSchemaObservation]):
    """Schema introspection tool."""

    @classmethod
    def create(
        cls,
        conv_state: "ConversationState | None" = None,
        db_url: str = "",
        **kwargs: Any,
    ) -> Sequence["IntrospectSchemaTool"]:
        if not db_url:
            raise ValueError("db_url is required for IntrospectSchemaTool")
        return [
            cls(
                description=TOOL_DESCRIPTION,
                action_type=IntrospectSchemaAction,
                observation_type=IntrospectSchemaObservation,
                annotations=ToolAnnotations(
                    title="introspect_schema",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=IntrospectSchemaExecutor(db_url),
            )
        ]
