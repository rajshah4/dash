"""Save persistent learnings tool (Layer 5).

When the agent discovers something about the data — a schema quirk,
a type gotcha, an error pattern — it should save it so future sessions
don't repeat the same mistake.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

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


class SaveLearningAction(Action):
    """Save a discovery about the data for future sessions."""

    category: Literal["schema_quirk", "type_gotcha", "error_fix", "data_pattern", "performance"] = Field(
        description=(
            "Category of learning: "
            "schema_quirk (unexpected schema behavior), "
            "type_gotcha (column type issues), "
            "error_fix (how to fix a specific error), "
            "data_pattern (observed data patterns or anomalies), "
            "performance (query performance observations)"
        )
    )
    description: str = Field(
        description="Clear, actionable description of the learning"
    )
    tables_affected: list[str] | None = Field(
        default=None, description="Tables this learning applies to"
    )
    example: str | None = Field(
        default=None, description="Short example (SQL snippet or value) illustrating the learning"
    )


class SaveLearningObservation(Observation):
    """Result of saving a learning."""

    pass


# ============================================================================
# Executor
# ============================================================================


class SaveLearningExecutor(ToolExecutor[SaveLearningAction, SaveLearningObservation]):
    """Save learnings to the knowledge directory."""

    def __init__(self, learnings_dir: Path) -> None:
        self.learnings_dir = learnings_dir
        self.learnings_dir.mkdir(parents=True, exist_ok=True)

    def __call__(
        self,
        action: SaveLearningAction,
        conversation: "LocalConversation | None" = None,
    ) -> SaveLearningObservation:
        if not action.description or not action.description.strip():
            return SaveLearningObservation.from_text("Error: Description required.", is_error=True)

        # Check for duplicates — don't save the same learning twice
        existing = self._load_existing()
        for lr in existing:
            if lr.get("description", "").strip().lower() == action.description.strip().lower():
                return SaveLearningObservation.from_text(
                    f"Learning already exists: {action.description[:60]}… Skipped."
                )

        payload: dict[str, Any] = {
            "category": action.category,
            "description": action.description.strip(),
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
        if action.tables_affected:
            payload["tables_affected"] = action.tables_affected
        if action.example:
            payload["example"] = action.example.strip()

        try:
            # Generate filename from timestamp + category
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            slug = action.description[:40].strip().replace(" ", "_").lower()
            slug = "".join(c for c in slug if c.isalnum() or c == "_")
            filename = f"{ts}_{slug}.json"
            filepath = self.learnings_dir / filename

            with open(filepath, "w") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            return SaveLearningObservation.from_text(
                f"Saved learning ({action.category}): {action.description[:80]}…\n"
                f"File: {filepath}\n"
                f"This will be available in future sessions."
            )
        except OSError as e:
            logger.error(f"Failed to save learning: {e}")
            return SaveLearningObservation.from_text(f"Error: {e}", is_error=True)

    def _load_existing(self) -> list[dict[str, Any]]:
        """Load all existing learnings to check for duplicates."""
        learnings: list[dict[str, Any]] = []
        for filepath in self.learnings_dir.glob("*.json"):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    learnings.extend(data)
                elif isinstance(data, dict):
                    learnings.append(data)
            except (json.JSONDecodeError, OSError):
                pass
        return learnings

    def close(self) -> None:
        pass


# ============================================================================
# Tool Definition
# ============================================================================


TOOL_DESCRIPTION = """\
Save a discovery about the data that will persist across sessions.

Use this when you discover something the agent should remember:
- Schema quirks (unexpected column types, naming inconsistencies)
- Type gotchas (TEXT vs INTEGER for position columns)
- Error fixes (how to handle date parsing, NULL values)
- Data patterns (value ranges, common anomalies)
- Performance tips (which JOINs are slow, better alternatives)

Call this AFTER you've confirmed the discovery — don't save guesses.
Learnings are loaded into the system prompt for all future sessions.
"""


class SaveLearningTool(ToolDefinition[SaveLearningAction, SaveLearningObservation]):
    """Persistent learnings tool."""

    @classmethod
    def create(
        cls,
        conv_state: "ConversationState | None" = None,
        learnings_dir: str = "",
        **kwargs: Any,
    ) -> Sequence["SaveLearningTool"]:
        if not learnings_dir:
            raise ValueError("learnings_dir is required for SaveLearningTool")
        return [
            cls(
                description=TOOL_DESCRIPTION,
                action_type=SaveLearningAction,
                observation_type=SaveLearningObservation,
                annotations=ToolAnnotations(
                    title="save_learning",
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=SaveLearningExecutor(Path(learnings_dir)),
            )
        ]
