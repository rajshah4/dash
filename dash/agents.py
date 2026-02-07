"""
Dash Agents
===========

Defines the Dash data agent using the OpenHands SDK.

Two modes are available:
  - **SDK mode** (default): lightweight, uses custom SQL tools only.
  - **Platform mode**: runs on the full OpenHands server with bash, file
    editing, and browser tools alongside the custom SQL tools.

Six layers of context:
  1. Table Usage          — knowledge/tables/*.json → semantic model
  2. Human Annotations    — knowledge/business/*.json → business rules
  3. Query Patterns       — knowledge/queries/*.sql → validated SQL patterns
  4. Institutional Knowledge — MCP connectors (optional)
  5. Learnings            — knowledge/learnings/*.json → persistent discoveries
  6. Runtime Context      — introspect_schema tool → live schema inspection

Test: python -m dash.agents
"""

import json
from os import getenv
from pathlib import Path

from openhands.sdk import Agent, AgentContext, LLM, Tool, register_tool
from openhands.sdk.context.condenser.llm_summarizing_condenser import LLMSummarizingCondenser
from openhands.sdk.context.skills.skill import Skill
from openhands.sdk.logger import get_logger
from openhands.sdk.security.confirmation_policy import ConfirmRisky
from openhands.sdk.security.risk import SecurityRisk

from dash.context.business_rules import BUSINESS_CONTEXT
from dash.context.learnings import LEARNINGS_CONTEXT
from dash.context.query_patterns import QUERY_PATTERNS_CONTEXT
from dash.context.semantic_model import SEMANTIC_MODEL_STR
from dash.paths import LEARNINGS_DIR, QUERIES_DIR
from dash.tools.introspect import IntrospectSchemaTool
from dash.tools.save_learning import SaveLearningTool
from dash.tools.save_query import SaveValidatedQueryTool
from dash.tools.sql import RunSQLTool
from db import db_url

logger = get_logger(__name__)

# Paths to custom system prompts (replace the SDK's default coding-agent prompt)
PROMPT_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT_FILE = str(PROMPT_DIR / "system_prompt.j2")
SYSTEM_PROMPT_PLATFORM_FILE = str(PROMPT_DIR / "system_prompt_platform.j2")

# ============================================================================
# Register custom tools
# ============================================================================

register_tool(RunSQLTool.name, RunSQLTool)
register_tool(IntrospectSchemaTool.name, IntrospectSchemaTool)
register_tool(SaveValidatedQueryTool.name, SaveValidatedQueryTool)
register_tool(SaveLearningTool.name, SaveLearningTool)

# ============================================================================
# LLM Configuration
# ============================================================================

llm = LLM(
    model=getenv("LLM_MODEL", "openai/gpt-4.1"),
    api_key=getenv("LLM_API_KEY") or getenv("OPENAI_API_KEY"),
    base_url=getenv("LLM_BASE_URL"),
)

# ============================================================================
# Condenser — summarize context when conversations get long
# ============================================================================
# When the conversation exceeds max_size messages, older messages are
# summarized by the LLM to keep context within token limits while
# preserving key facts the agent discovered (schema quirks, column types, etc.)

condenser = LLMSummarizingCondenser(
    llm=llm,
    max_size=100,   # Summarize after 100 events
    keep_first=2,   # Always keep the system prompt + first user message
)

# ============================================================================
# Security — confirmation policy for risky actions
# ============================================================================
# ConfirmRisky pauses and asks for user confirmation when the LLM
# predicts an action has HIGH or UNKNOWN risk. Since Dash only runs
# read-only SQL, this is mostly a safety net for the save_validated_query tool.

confirmation_policy = ConfirmRisky(
    threshold=SecurityRisk.HIGH,
    confirm_unknown=True,
)

# ============================================================================
# Domain Knowledge — all 6 layers assembled into a single skill
# ============================================================================
# Layer 1: Table Usage (semantic model)
# Layer 2: Human Annotations (business rules, metrics, gotchas)
# Layer 3: Query Patterns (validated SQL that works)
# Layer 5: Learnings (persistent discoveries from previous sessions)
# (Layer 4: Institutional Knowledge is handled by MCP at runtime)
# (Layer 6: Runtime Context is handled by introspect_schema at runtime)

_sections = [
    f"## SEMANTIC MODEL\n\n{SEMANTIC_MODEL_STR}" if SEMANTIC_MODEL_STR else "",
    BUSINESS_CONTEXT,
    QUERY_PATTERNS_CONTEXT,
    LEARNINGS_CONTEXT,
]
DOMAIN_KNOWLEDGE = "\n---\n\n".join(s for s in _sections if s)

# ============================================================================
# Agent Context (provides the Dash skill/instructions)
# ============================================================================

dash_skill = Skill(
    name="dash-data-analyst",
    content=DOMAIN_KNOWLEDGE,
    description="Semantic model, business rules, validated query patterns, and learnings for the F1 database",
)

dash_context = AgentContext(
    skills=[dash_skill],
)

# ============================================================================
# MCP Configuration (optional — Layer 4: Institutional Knowledge)
# ============================================================================
# Connect to external MCP tool servers. Configure via:
#   1. DASH_MCP_CONFIG env var (JSON string)
#   2. DASH_MCP_CONFIG_FILE env var (path to JSON file)
#   3. Default: dash/mcp_config.json (if it exists)
#
# Format (standard MCP config):
#   {
#     "mcpServers": {
#       "server-name": {
#         "command": "uvx",
#         "args": ["mcp-server-name"]
#       }
#     }
#   }


def _load_mcp_config() -> dict | None:
    """Load MCP configuration from env var, file, or default path."""
    # 1. Inline JSON from env var
    raw = getenv("DASH_MCP_CONFIG")
    if raw:
        try:
            config = json.loads(raw)
            logger.info("Loaded MCP config from DASH_MCP_CONFIG env var")
            return config
        except json.JSONDecodeError:
            logger.warning("DASH_MCP_CONFIG is not valid JSON, ignoring")

    # 2. Path from env var
    config_path_str = getenv("DASH_MCP_CONFIG_FILE")
    if config_path_str:
        config_path = Path(config_path_str)
    else:
        # 3. Default path
        config_path = Path(__file__).parent / "mcp_config.json"

    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            logger.info("Loaded MCP config from %s", config_path)
            return config
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load MCP config from %s: %s", config_path, e)

    return None


mcp_config = _load_mcp_config()

# ============================================================================
# Shared tool list
# ============================================================================

_TOOLS = [
    Tool(name=RunSQLTool.name, params={"db_url": db_url}),
    Tool(name=IntrospectSchemaTool.name, params={"db_url": db_url}),
    Tool(name=SaveValidatedQueryTool.name, params={"queries_dir": str(QUERIES_DIR)}),
    Tool(name=SaveLearningTool.name, params={"learnings_dir": str(LEARNINGS_DIR)}),
]

# ============================================================================
# SDK Agent (lightweight — custom SQL tools only)
# ============================================================================

dash = Agent(
    llm=llm,
    tools=_TOOLS,
    agent_context=dash_context,
    condenser=condenser,
    system_prompt_filename=SYSTEM_PROMPT_FILE,
    mcp_config=mcp_config or {},
    include_default_tools=[],
)

# ============================================================================
# Platform Agent (full OpenHands server — bash, file editing, browser + SQL)
# ============================================================================
# When running on the OpenHands platform (via RemoteConversation), the server
# provides additional tools (bash, file editor, browser). The platform agent
# includes FinishTool and ThinkTool which the server's loop requires, and uses
# a system prompt that teaches Dash to leverage bash for formatted SQL output,
# Python scripts for analysis/charts, and file editing for knowledge curation.

dash_platform = Agent(
    llm=llm,
    tools=_TOOLS,
    agent_context=dash_context,
    condenser=condenser,
    system_prompt_filename=SYSTEM_PROMPT_PLATFORM_FILE,
    mcp_config=mcp_config or {},
    include_default_tools=["FinishTool", "ThinkTool"],
)


if __name__ == "__main__":
    from openhands.sdk import Conversation

    conversation = Conversation(agent=dash, workspace=".")
    conversation.set_confirmation_policy(confirmation_policy)
    conversation.send_message("Who won the most races in 2019?")
    conversation.run()
    print("Done!")
