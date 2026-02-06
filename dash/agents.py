"""
Dash Agents
===========

Defines the Dash data agent using the OpenHands SDK.

Features:
- Custom SQL tools (run_sql, introspect_schema, save_validated_query)
- LLM-summarizing condenser for long conversations
- Security confirmation policy for risky actions

Test: python -m dash.agents
"""

from os import getenv
from pathlib import Path

from openhands.sdk import Agent, AgentContext, LLM, Tool, register_tool
from openhands.sdk.context.condenser.llm_summarizing_condenser import LLMSummarizingCondenser
from openhands.sdk.context.skills.skill import Skill
from openhands.sdk.security.confirmation_policy import ConfirmRisky
from openhands.sdk.security.risk import SecurityRisk

from dash.context.business_rules import BUSINESS_CONTEXT
from dash.context.semantic_model import SEMANTIC_MODEL_STR
from dash.paths import QUERIES_DIR
from dash.tools.introspect import IntrospectSchemaTool
from dash.tools.save_query import SaveValidatedQueryTool
from dash.tools.sql import RunSQLTool
from db import db_url

# Absolute path to our custom system prompt (replaces the SDK's coding-agent prompt)
PROMPT_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT_FILE = str(PROMPT_DIR / "system_prompt.j2")

# ============================================================================
# Register custom tools
# ============================================================================

register_tool(RunSQLTool.name, RunSQLTool)
register_tool(IntrospectSchemaTool.name, IntrospectSchemaTool)
register_tool(SaveValidatedQueryTool.name, SaveValidatedQueryTool)

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
# Instructions (injected as a Skill)
# ============================================================================

DOMAIN_KNOWLEDGE = f"""\
## SEMANTIC MODEL

{SEMANTIC_MODEL_STR}
---

{BUSINESS_CONTEXT}\
"""

# ============================================================================
# Agent Context (provides the Dash skill/instructions)
# ============================================================================

dash_skill = Skill(
    name="dash-data-analyst",
    content=DOMAIN_KNOWLEDGE,
    description="Semantic model and business rules for the F1 database",
)

dash_context = AgentContext(
    skills=[dash_skill],
)

# ============================================================================
# Create Agent
# ============================================================================

dash = Agent(
    llm=llm,
    tools=[
        Tool(name=RunSQLTool.name, params={"db_url": db_url}),
        Tool(name=IntrospectSchemaTool.name, params={"db_url": db_url}),
        Tool(name=SaveValidatedQueryTool.name, params={"queries_dir": str(QUERIES_DIR)}),
    ],
    agent_context=dash_context,
    condenser=condenser,
    system_prompt_filename=SYSTEM_PROMPT_FILE,
    include_default_tools=[],
)

if __name__ == "__main__":
    from openhands.sdk import Conversation

    conversation = Conversation(agent=dash, workspace=".")
    conversation.set_confirmation_policy(confirmation_policy)
    conversation.send_message("Who won the most races in 2019?")
    conversation.run()
    print("Done!")
