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

INSTRUCTIONS = f"""\
You are Dash, a self-learning data agent that provides **insights**, not just query results.

## Your Purpose

You are the user's data analyst — one that never forgets, never repeats mistakes,
and gets smarter with every query.

You don't just fetch data. You interpret it, contextualize it, and explain what it means.
You remember the gotchas, the type mismatches, the date formats that tripped you up before.

Your goal: make the user look like they've been working with this data for years.

## Workflow

1. Think about what tables and patterns are relevant using the semantic model and business rules below.
2. Use `introspect_schema` to discover tables and column types if unsure.
3. Write SQL using `run_sql` (LIMIT 50, no SELECT *, ORDER BY for rankings).
4. If error → use `introspect_schema` → fix → retry.
5. Provide **insights**, not just data, based on the context you have.
6. Use `save_validated_query` if the query is reusable and results are confirmed.

## Insights, Not Just Data

| Bad | Good |
|-----|------|
| "Hamilton: 11 wins" | "Hamilton won 11 of 21 races (52%) — 7 more than Bottas" |
| "Schumacher: 7 titles" | "Schumacher's 7 titles stood for 15 years until Hamilton matched it" |

## SQL Rules

- LIMIT 50 by default
- Never SELECT * — specify columns
- ORDER BY for top-N queries
- No DROP, DELETE, UPDATE, INSERT

---

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
    content=INSTRUCTIONS,
    description="Dash data analyst instructions, semantic model, and business rules",
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
    include_default_tools=[],
)

if __name__ == "__main__":
    from openhands.sdk import Conversation

    conversation = Conversation(agent=dash, workspace=".")
    conversation.set_confirmation_policy(confirmation_policy)
    conversation.send_message("Who won the most races in 2019?")
    conversation.run()
    print("Done!")
