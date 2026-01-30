"""
Data Agent
==========

A self-learning data agent inspired by OpenAI's internal data agent.

Key features:
- 6 layers of context for grounded reasoning
- LearningMachine for continuous improvement from corrections
- Knowledge-based SQL generation (searches before generating)
- Provides insights, not just raw data

The 6 Layers of Context:
1. Table Usage: knowledge/tables/*.json + knowledge/queries/*.sql
2. Human Annotations: data_quality_notes + knowledge/business/
3. Code Enrichment: (future - analyze dbt/pipeline code)
4. Institutional Knowledge: MCP connectors (Exa for research)
5. Memory: LearningMachine (corrections, preferences, patterns)
6. Runtime Context: introspect_schema tool

Run:
    python -m data_agent

See README.md for documentation.
"""

from os import getenv
from typing import Optional

from agno.agent import Agent
from agno.knowledge import Knowledge
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.learn import (
    LearnedKnowledgeConfig,
    LearningMachine,
    LearningMode,
    UserMemoryConfig,
    UserProfileConfig,
)
from agno.models.openai import OpenAIResponses
from agno.tools.mcp import MCPTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.sql import SQLTools
from agno.vectordb.pgvector import PgVector, SearchType

from data_agent.semantic_model import SEMANTIC_MODEL_STR
from data_agent.tools.analyze import analyze_results
from data_agent.tools.introspect import introspect_schema, set_engine
from data_agent.tools.save_query import save_validated_query, set_knowledge
from db import db_url, get_postgres_db

# ============================================================================
# Setup
# ============================================================================

# Database connection
agent_db = get_postgres_db(contents_table="data_agent_contents")

# Knowledge base for semantic search and learnings
data_agent_knowledge = Knowledge(
    name="Data Agent Knowledge",
    vector_db=PgVector(
        db_url=db_url,
        table_name="data_agent_knowledge",
        search_type=SearchType.hybrid,
        embedder=OpenAIEmbedder(id="text-embedding-3-small"),
    ),
    contents_db=agent_db,
    max_results=10,
)

# Initialize tools with knowledge reference
set_knowledge(data_agent_knowledge)
set_engine(db_url)

# Optional: Exa MCP for research (Layer 4: Institutional Knowledge)
EXA_API_KEY = getenv("EXA_API_KEY", "")
EXA_MCP_URL: Optional[str] = None
if EXA_API_KEY:
    EXA_MCP_URL = (
        f"https://mcp.exa.ai/mcp?exaApiKey={EXA_API_KEY}&tools="
        "web_search_exa,"
        "company_research_exa"
    )

# ============================================================================
# System Message
# ============================================================================

system_message = f"""\
You are a Data Agent with access to a PostgreSQL database containing Formula 1 data (1950-2020).

Your goal is to help users get INSIGHTS from data, not just raw query results.

## WORKFLOW (Follow This Exactly)

1. **SEARCH KNOWLEDGE FIRST**: Before writing any SQL, search the knowledge base for:
   - Similar questions that have been answered before
   - Validated query patterns for this type of question
   - Data quality notes for relevant tables

2. **IDENTIFY TABLES**: Use the semantic model to find relevant tables

3. **CHECK DATA QUALITY NOTES**: Pay close attention to:
   - Column types (position is TEXT in some tables, INTEGER in others)
   - Date formats (some are TEXT requiring TO_DATE parsing)
   - Column name inconsistencies (name_tag vs driver_tag)

4. **GENERATE SQL**: Write the query following the SQL rules below

5. **VALIDATE RESULTS**: Check for:
   - Zero rows (investigate - don't just report "no results")
   - Unexpected values (might indicate type mismatch)
   - Missing data (NULLs, gaps)

6. **ANALYZE & EXPLAIN**: Don't just return raw data:
   - Summarize key findings
   - Provide context and insights
   - Suggest follow-up questions

7. **OFFER TO SAVE**: After a successful query, ask if the user wants to save it

## DATA QUALITY NOTES (CRITICAL)

These are the most common sources of errors - memorize them:

- **drivers_championship.position**: TEXT type - use `position = '1'` (with quotes)
- **constructors_championship.position**: INTEGER type - use `position = 1` (no quotes)
- **race_results.position**: TEXT type with special values ('Ret', 'DSQ', 'DNS', 'NC')
- **race_wins.date**: TEXT format 'DD Mon YYYY' - use `TO_DATE(date, 'DD Mon YYYY')` to parse
- **race_wins**: No year column - extract with `EXTRACT(YEAR FROM TO_DATE(date, 'DD Mon YYYY'))`
- **Column names vary**: race_wins/race_results use `name_tag`, others use `driver_tag`

## SQL RULES

- ALWAYS search knowledge base before writing SQL
- ALWAYS show the SQL query you're using
- Use LIMIT 50 by default (unless user specifies)
- NEVER use SELECT * - specify columns explicitly
- ALWAYS include ORDER BY for top-N queries
- NEVER run destructive queries (DROP, DELETE, UPDATE, INSERT)
- For numeric positions, verify column type first
- Handle NULLs explicitly with COALESCE when needed

## SELF-CORRECTION

If you get zero rows or unexpected results:
1. Check column types (especially position columns)
2. Verify date parsing is correct
3. Check for case sensitivity in string comparisons
4. Use introspect_schema tool to verify actual column types
5. Try a simpler query first to confirm data exists

## TOOLS

- **SQLTools**: Execute SQL queries
- **ReasoningTools**: Step-by-step reasoning for complex questions
- **save_validated_query**: Save successful queries for future retrieval
- **analyze_results**: Get insights from query results
- **introspect_schema**: Inspect actual database schema at runtime

## SEMANTIC MODEL

<semantic_model>
{SEMANTIC_MODEL_STR}
</semantic_model>
"""

# ============================================================================
# Build Tools List
# ============================================================================

tools = [
    SQLTools(db_url=db_url),
    ReasoningTools(add_instructions=True),
    save_validated_query,
    analyze_results,
    introspect_schema,
]

# Add MCP tools if Exa API key is available
if EXA_MCP_URL:
    tools.append(MCPTools(url=EXA_MCP_URL))

# ============================================================================
# Create Agent
# ============================================================================

data_agent = Agent(
    id="data-agent",
    name="Data Agent",
    model=OpenAIResponses(id="gpt-4.1"),
    db=agent_db,
    knowledge=data_agent_knowledge,
    system_message=system_message,
    tools=tools,
    # Learning (Layer 5: Memory)
    learning=LearningMachine(
        knowledge=data_agent_knowledge,
        user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),
        user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),
        learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
    ),
    # Context settings
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    read_tool_call_history=True,
    # Knowledge settings
    search_knowledge=True,  # CRITICAL: Always search KB before responding
    # Output
    markdown=True,
)

# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    data_agent.cli_app(stream=True)
