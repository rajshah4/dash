# Knowledge and Context

Dash reduces SQL failures by grounding the agent in a layered knowledge system and a self-learning loop. This document explains the six layers, how learning works, and how to add or validate knowledge.

## The Six Layers of Context

This architecture follows [OpenAI's approach to building their in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/). Each layer adds context that makes SQL generation more reliable.

| Layer | Purpose | SDK Mode | Platform Mode |
|-------|---------|----------|---------------|
| 1. **Table Usage** | Schema, columns, types, relationships | `knowledge/tables/*.json` → loaded into prompt via `semantic_model.py` | `skills/dash-schema.md` → auto-injected as a skill |
| 2. **Human Annotations** | Metrics, definitions, business rules | `knowledge/business/*.json` → loaded via `business_rules.py` | `skills/dash-sql-patterns.md` (business rules section) |
| 3. **Query Patterns** | SQL that is known to work | `knowledge/queries/*.sql` → loaded via `query_patterns.py` | `skills/dash-sql-patterns.md` (validated queries) |
| 4. **Institutional Knowledge** | Docs, wikis, external references | MCP connectors (optional) | MCP or `psql` + Python in sandbox |
| 5. **Learnings** | Error patterns and discovered fixes | `save_learning` tool → `knowledge/learnings/*.json` | Agent saves to `knowledge/` via file editor |
| 6. **Runtime Context** | Live schema on demand | `introspect_schema` tool | `psql -c "\d table_name"` in terminal |

**SDK Mode**: Layers 1-3 and 5 are loaded at startup into the agent's prompt as a `Skill`. Layer 4 connects via MCP. Layer 6 discovers live schema on demand via a custom tool.

**Platform Mode**: All 6 layers are delivered to OpenHands's coding agent via **skills** — markdown files mounted into the server's `/app/skills/` directory and auto-injected into every conversation. The agent uses `psql` (pre-installed in a custom sandbox image) and Python for queries and analysis.

## The Self-Learning Loop

Dash improves without retraining or fine-tuning. We call this gpu-poor continuous learning.

```
User Question
     ↓
Load Knowledge (semantic model + business rules + query patterns + learnings)
     ↓
Reason about intent — check existing patterns first
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
 ↓                                    ↓
Return insight                   save_learning (schema quirk)
 ↓
Optionally save_validated_query
```

Two tools drive the learning loop:

- **`save_validated_query`** — saves working SQL as `.sql` patterns (same format as curated queries). Loaded into the prompt for all future sessions.
- **`save_learning`** — saves discovered patterns (schema quirks, type gotchas, error fixes) as JSON. Loaded into the prompt for all future sessions.

**Knowledge** is curated — validated queries and business context you want the agent to build on.

**Learnings** are discovered — when a query fails because `position` is TEXT not INTEGER, the agent introspects, self-corrects, and saves the discovery so it never makes the same mistake again.

## Adding Knowledge

Dash works best when it understands how your organization talks about data.

```
knowledge/
├── tables/      # Table meaning and caveats (Layer 1)
├── business/    # Metrics and language (Layer 2)
├── queries/     # Proven SQL patterns (Layer 3)
└── learnings/   # Discovered patterns from sessions (Layer 5)

skills/           # Platform mode — auto-loaded into OpenHands agent
├── dash-agent.md       # Agent identity + workflow
├── dash-schema.md      # Table metadata + data quality gotchas
└── dash-sql-patterns.md # Validated SQL + business rules
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

## Schema Drift Detection

```sh
python -m dash.scripts.check_schema          # compare knowledge vs live DB
python -m dash.scripts.check_schema --fix    # auto-create missing knowledge files
```
