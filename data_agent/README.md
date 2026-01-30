# Data Agent

A self-learning data agent inspired by [OpenAI's internal data agent](https://openai.com/index/how-openai-built-its-data-agent/).

## What Makes This Different

Most text-to-SQL tools fail because of **missing context**, not model limitations. This agent implements the **6 layers of context** approach:

| Layer | Purpose | Implementation |
|-------|---------|----------------|
| 1. Table Usage | Schema metadata, historical queries | `knowledge/tables/`, `knowledge/queries/` |
| 2. Human Annotations | Expert descriptions, caveats | `data_quality_notes`, `knowledge/business/` |
| 3. Code Enrichment | Pipeline definitions | (Future) |
| 4. Institutional Knowledge | External context | MCP connectors (Exa) |
| 5. Memory | Corrections, preferences | `LearningMachine` |
| 6. Runtime Context | Live schema inspection | `introspect_schema` tool |

Key insight: **The agent searches knowledge before generating SQL**, and **learns from corrections** to continuously improve.

## Quick Start

```bash
# 1. Start PostgreSQL (via Docker Compose or your own instance)
docker compose up -d

# 2. Load the F1 sample data
python -m data_agent.scripts.load_data

# 3. Load the knowledge base
python -m data_agent.scripts.load_knowledge

# 4. Run the agent
python -m data_agent
```

## Example Queries

```
> Who won the most races in 2019?
Lewis Hamilton won the most races in 2019 with 11 wins.

> Which driver has won the most world championships?
Michael Schumacher with 7 championships.

> Compare Ferrari vs Mercedes from 2015-2020
[Returns comparative analysis with insights]

> How did Red Bull perform in 2020?
[Provides performance summary with key findings]
```

## Architecture

```
data_agent/
├── agent.py           # Main agent with LearningMachine
├── semantic_model.py  # Schema from knowledge files
├── knowledge/
│   ├── tables/        # Layer 1+2: Table metadata
│   ├── queries/       # Layer 1: Validated SQL patterns
│   └── business/      # Layer 2: Business definitions
├── tools/
│   ├── save_query.py  # Save queries for learning
│   ├── analyze.py     # Insights, not just data
│   └── introspect.py  # Runtime schema inspection
├── evals/             # Evaluation harness
└── scripts/           # Data loading utilities
```

### The Learning Loop

1. User asks a question
2. Agent searches knowledge base for similar questions
3. If found: adapts validated pattern
4. If not: generates SQL, handles data quality issues
5. Agent provides insights (not just raw data)
6. On success, offers to save the query for future use
7. Corrections are captured by LearningMachine

## Key Features

### 1. Knowledge-Based SQL Generation

The agent **always searches the knowledge base first**. This means:
- Previously validated queries are reused
- Data quality notes are applied automatically
- Business rules are considered

### 2. LearningMachine Integration

From Agno's `LearningMachine`:
- **User Profile**: Tracks preferences (SQL style, detail level)
- **User Memory**: Remembers corrections and context
- **Learned Knowledge**: Saves successful patterns

### 3. Data Quality Handling

The agent knows about common data issues:
- `position` column is TEXT in some tables, INTEGER in others
- Dates in `race_wins` require `TO_DATE()` parsing
- Column names vary (`name_tag` vs `driver_tag`)

### 4. Insights, Not Just Data

The `analyze_results` tool provides:
- Key findings summary
- Statistics for numeric columns
- Suggested follow-up questions

## Adding Your Own Data

1. **Load your data** into PostgreSQL

2. **Create table metadata** in `knowledge/tables/your_table.json`:
   ```json
   {
     "table_name": "your_table",
     "table_description": "What this table contains",
     "use_cases": ["Example query 1", "Example query 2"],
     "data_quality_notes": ["Important notes about data types, formats"],
     "table_columns": [
       {"name": "col1", "type": "text", "description": "What this column contains"}
     ]
   }
   ```

3. **Add business definitions** in `knowledge/business/your_metrics.json`:
   ```json
   {
     "metrics": [
       {"name": "Your Metric", "definition": "...", "table": "...", "calculation": "..."}
     ],
     "business_rules": ["Important rule 1"],
     "common_gotchas": [
       {"issue": "Common mistake", "tables_affected": ["..."], "solution": "..."}
     ]
   }
   ```

4. **Reload knowledge**:
   ```bash
   python -m data_agent.scripts.load_knowledge
   ```

## Evaluation

Run the evaluation suite:

```bash
# All tests
python -m data_agent.evals.run_evals

# By category
python -m data_agent.evals.run_evals --category basic
python -m data_agent.evals.run_evals --category data_quality

# Verbose output
python -m data_agent.evals.run_evals --verbose
```

Categories:
- `basic`: Simple queries
- `aggregation`: GROUP BY, COUNT, etc.
- `data_quality`: Type mismatch handling
- `complex`: Multi-table queries
- `edge_case`: Special cases

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_USER` | PostgreSQL user | `ai` |
| `DB_PASS` | PostgreSQL password | `ai` |
| `DB_DATABASE` | PostgreSQL database | `ai` |
| `EXA_API_KEY` | (Optional) Exa API key for research | - |

## References

- [How OpenAI Built Its Data Agent](https://openai.com/index/how-openai-built-its-data-agent/)
- [Agno Documentation](https://docs.agno.com)
- [LearningMachine](https://docs.agno.com/learning)
