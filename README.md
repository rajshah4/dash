# Dash

Dash is a **self-learning data agent** that grounds its answers in **6 layers of context** and improves with every run. Built on the [OpenHands Software Agent SDK](https://docs.openhands.dev/sdk).

Inspired by [OpenAI's in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/).

## Quick Start

```sh
# Clone this repo
git clone https://github.com/rajshah4/dash.git && cd dash

# Set your LLM API key
cp example.env .env
# Edit .env with your API key (any LiteLLM-supported provider works)

# Start the database
docker compose up -d dash-db

# Setup and activate virtual environment
./scripts/venv_setup.sh && source .venv/bin/activate

# Load sample data
python -m dash.scripts.load_data

# Run Dash
python -m dash
```

**Try it** (sample F1 dataset):

- Who won the most F1 World Championships?
- How many races has Lewis Hamilton won?
- Compare Ferrari vs Mercedes points 2015-2020

## Why Text-to-SQL Breaks in Practice

Our goal is simple: ask a question in english, get a correct, meaningful answer. But raw LLMs writing SQL hit a wall fast:

- **Schemas lack meaning.**
- **Types are misleading.**
- **Tribal knowledge is missing.**
- **No way to learn from mistakes.**
- **Results generally lack interpretation.**

The root cause is missing context and missing memory.

Dash solves this with **6 layers of grounded context**, a **self-learning loop** that improves with every query, and a focus on **understanding your question** to deliver insights you can act on.

## The Six Layers of Context

| Layer | Purpose | Implementation |
|-------|---------|----------------|
| 1. **Table Usage** | Schema, columns, relationships | `knowledge/tables/*.json` |
| 2. **Human Annotations** | Metrics, definitions, and business rules | `knowledge/business/*.json` |
| 3. **Query Patterns** | SQL that is known to work | `knowledge/queries/*.sql` |
| 4. **Institutional Knowledge** | Docs, wikis, external references | MCP connectors (optional) |
| 5. **Learnings** | Error patterns and discovered fixes | `save_validated_query` tool + condenser |
| 6. **Runtime Context** | Live schema changes | `introspect_schema` tool |

The agent retrieves relevant context at query time, then generates SQL grounded in patterns that already work.

## The Self-Learning Loop

Dash improves without retraining or fine-tuning. We call this gpu-poor continuous learning.

```
User Question
     ↓
Load Knowledge (semantic model + business rules)
     ↓
Reason about intent
     ↓
Generate grounded SQL
     ↓
Execute and interpret
     ↓
 ┌────┴────┐
 ↓         ↓
Success    Error
 ↓         ↓
 ↓         Introspect schema → Fix → Retry
 ↓
Return insight
 ↓
Optionally save as validated query
```

**Knowledge** is curated — validated queries and business context you want the agent to build on.

**Runtime learning** is discovered — when a query fails because `position` is TEXT not INTEGER, the agent introspects the schema and self-corrects. Validated queries are saved for future reuse.

## Insights, Not Just Rows

Dash reasons about what makes an answer useful, not just technically correct.

**Question:**
Who won the most races in 2019?

| Typical SQL Agent | Dash |
|------------------|------|
| `Hamilton: 11` | Lewis Hamilton dominated 2019 with **11 wins out of 21 races**, more than double Bottas's 4 wins. This performance secured his sixth world championship. |

## How It Works

Dash is built on the [OpenHands Software Agent SDK](https://docs.openhands.dev/sdk):

| Component | Purpose |
|-----------|---------|
| **Custom Tools** | `run_sql`, `introspect_schema`, `save_validated_query` |
| **MCP** | Connect to external tool servers via [Model Context Protocol](https://modelcontextprotocol.io/) |
| **Custom System Prompt** | Data-agent prompt replacing the SDK's default coding-agent prompt |
| **Agent Context** | Semantic model and business rules injected as a `Skill` |
| **Condenser** | `LLMSummarizingCondenser` compresses long conversations |
| **Security** | `ConfirmRisky` confirmation policy for destructive actions |
| **Persistence** | Save/resume conversations to disk |
| **Tracing** | [Laminar](https://www.lmnr.ai) tracing (auto-enabled with `LMNR_PROJECT_API_KEY`) |

## Adding Knowledge

Dash works best when it understands how your organization talks about data.

```
knowledge/
├── tables/      # Table meaning and caveats
├── queries/     # Proven SQL patterns
└── business/    # Metrics and language
```

### Table Metadata

```json
{
  "table_name": "orders",
  "table_description": "Customer orders with denormalized line items",
  "use_cases": ["Revenue reporting", "Customer analytics"],
  "data_quality_notes": [
    "created_at is UTC",
    "status values: pending, completed, refunded",
    "amount stored in cents"
  ]
}
```

### Query Patterns

```sql
-- <query name>monthly_revenue</query name>
-- <query description>
-- Monthly revenue calculation.
-- Converts cents to dollars.
-- Excludes refunded orders.
-- </query description>
-- <query>
SELECT
    DATE_TRUNC('month', created_at) AS month,
    SUM(amount) / 100.0 AS revenue_dollars
FROM orders
WHERE status = 'completed'
GROUP BY 1
ORDER BY 1 DESC
-- </query>
```

### Business Rules

```json
{
  "metrics": [
    {
      "name": "MRR",
      "definition": "Sum of active subscriptions excluding trials"
    }
  ],
  "common_gotchas": [
    {
      "issue": "Revenue double counting",
      "solution": "Filter to completed orders only"
    }
  ]
}
```

### Validate Knowledge

```sh
python -m dash.scripts.load_knowledge
```

## Local Development

```sh
# Setup
./scripts/venv_setup.sh && source .venv/bin/activate
docker compose up -d dash-db
python -m dash.scripts.load_data

# Run
python -m dash                          # Interactive CLI
python -m dash "Who won in 2019?"       # One-shot query
python -m app.main                      # API server (FastAPI)

# Evals
python -m dash.evals.run_evals              # String matching
python -m dash.evals.run_evals -g           # LLM grader
python -m dash.evals.run_evals -g -r -v     # Full evaluation
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_API_KEY` | Yes | API key for your LLM provider ([any LiteLLM provider](https://docs.litellm.ai/docs/providers)) |
| `LLM_MODEL` | No | Model name (default: `openai/gpt-4.1`) |
| `LLM_BASE_URL` | No | Custom API base URL |
| `LMNR_PROJECT_API_KEY` | No | [Laminar](https://www.lmnr.ai) API key for tracing (auto-enabled) |
| `DASH_MCP_CONFIG` | No | MCP config as inline JSON (or use `DASH_MCP_CONFIG_FILE`) |
| `DASH_ENABLE_CONFIRMATION` | No | Enable security confirmation for risky actions (API) |
| `DASH_PERSISTENCE_DIR` | No | Custom session storage directory (API) |
| `DB_*` | No | Database config (defaults to `ai`/`ai`/`ai` on localhost) |

## Deploy with Docker

```sh
# Full stack (DB + API)
docker compose up -d --build

# Load data
docker exec -it dash-api python -m dash.scripts.load_data
```

## Acknowledgements

This repo is based on [agno-agi/dash](https://github.com/agno-agi/dash) by [Ashpreet Bedi](https://www.ashpreetbedi.com), refactored to use the [OpenHands Software Agent SDK](https://docs.openhands.dev/sdk). The 6-layer architecture and self-learning approach are inspired by [OpenAI's in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/).

## Further Reading

- [OpenAI's In-House Data Agent](https://openai.com/index/inside-our-in-house-data-agent/) — the inspiration
- [Self-Improving SQL Agent](https://www.ashpreetbedi.com/articles/sql-agent) — deep dive on an earlier architecture
- [agno-agi/dash](https://github.com/agno-agi/dash) — the original Agno implementation
- [OpenHands SDK Docs](https://docs.openhands.dev/sdk) — the framework Dash is built on
