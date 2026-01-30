# CLAUDE.md

## Project Overview

Data Agent - A self-learning data agent with 6 layers of context for grounded SQL generation.

## Structure

```
da/
├── agent.py              # Main agent (knowledge + learnings + memory)
├── paths.py              # Path constants
├── context/
│   ├── semantic_model.py # Layer 1: Table metadata
│   └── business_rules.py # Layer 2: Business rules
├── tools/
│   ├── analyze.py        # Result analysis
│   ├── introspect.py     # Layer 6: Runtime schema
│   ├── learnings.py      # Layer 5: Search/save learnings
│   └── save_query.py     # Save validated queries
├── scripts/
│   ├── load_data.py      # Load F1 sample data
│   └── load_knowledge.py # Load knowledge files
└── evals/
    ├── test_cases.py     # Test cases
    └── run_evals.py      # Run evaluations
```

## Commands

```bash
./scripts/venv_setup.sh && source .venv/bin/activate
./scripts/format.sh      # Format code
./scripts/validate.sh    # Lint + type check
python -m da.agent       # CLI mode
python -m da.evals.run_evals  # Run evals
```

## The 6 Layers

| Layer | Source | Code |
|-------|--------|------|
| 1. Table Metadata | `knowledge/tables/*.json` | `da/context/semantic_model.py` |
| 2. Business Rules | `knowledge/business/*.json` | `da/context/business_rules.py` |
| 3. Query Patterns | `knowledge/queries/*.sql` | Loaded into knowledge base |
| 4. External Knowledge | Exa MCP (optional) | `da/agent.py` |
| 5. Learnings | Custom tools | `da/tools/learnings.py` |
| 6. Runtime Context | `introspect_schema` | `da/tools/introspect.py` |

Plus `enable_agentic_memory=True` for user preferences.

## Agent Pattern

```python
from agno.agent import Agent
from agno.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType
from db import db_url, get_postgres_db

# Two knowledge bases: static (knowledge) + dynamic (learnings)
data_agent_knowledge = Knowledge(
    vector_db=PgVector(db_url=db_url, table_name="data_agent_knowledge", ...),
    contents_db=get_postgres_db(contents_table="data_agent_knowledge_contents"),
)

data_agent_learnings = Knowledge(
    vector_db=PgVector(db_url=db_url, table_name="data_agent_learnings", ...),
    contents_db=get_postgres_db(contents_table="data_agent_learnings_contents"),
)

# Create tools with dependencies injected
search_learnings, save_learning = create_learnings_tools(data_agent_learnings)

data_agent = Agent(
    knowledge=data_agent_knowledge,
    search_knowledge=True,
    enable_agentic_memory=True,
    tools=[..., search_learnings, save_learning],
)
```

## Data Quality (F1 Dataset)

| Issue | Solution |
|-------|----------|
| `position` is TEXT in `drivers_championship` | Use `position = '1'` |
| `position` is INTEGER in `constructors_championship` | Use `position = 1` |
| `date` is TEXT in `race_wins` | Use `TO_DATE(date, 'DD Mon YYYY')` |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `EXA_API_KEY` | No | Exa for web research |
| `DB_*` | No | Database config |

## Agno Reference

```python
# Models
from agno.models.openai import OpenAIResponses
model = OpenAIResponses(id="gpt-5.2")

# Knowledge
from agno.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType

# Tools
from agno.tools import tool
from agno.tools.sql import SQLTools

# Docs
# https://docs.agno.com/llms.txt
# https://docs.agno.com/llms-full.txt
```
