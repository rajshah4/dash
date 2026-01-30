# Data Agent Implementation Spec

**Goal**: Build an open-source data agent inspired by [OpenAI's internal data agent](https://openai.com/index/how-openai-built-its-data-agent/) that goes from question → insight in minutes.

**Reference Article**: https://openai.com/index/how-openai-built-its-data-agent/

---

## Background: What OpenAI Built

OpenAI's data agent serves 3.5k internal users across 600 PB of data in 70k datasets. The key insight from their article:

> "Most Text-to-SQL failures are not 'model is dumb', they're 'model is missing context and tribal knowledge' issues."

Their agent works because of **6 layers of context**:

| Layer | Purpose | Our Implementation |
|:------|:--------|:-------------------|
| 1. Table Usage | Schema metadata, lineage, historical queries | `knowledge/tables/*.json` + `knowledge/queries/*.sql` |
| 2. Human Annotations | Expert descriptions, business meaning, caveats | `data_quality_notes` + `knowledge/business/` |
| 3. Codex Enrichment | Code-level definitions of how tables are built | Future: analyze dbt/pipeline code |
| 4. Institutional Knowledge | Slack, Docs, Notion - company context | MCP connectors (Exa for now, Slack/Docs later) |
| 5. Memory | Corrections, filters, user preferences | Agno's `LearningMachine` |
| 6. Runtime Context | Live queries when context is stale | `introspect_schema` tool |

Key quote from OpenAI:
> "When the agent is given corrections or discovers nuances about certain data questions, it's able to save these learnings for next time, allowing it to constantly improve with its users."

---

## What We're Building

Merge the best of:
- **text_to_sql agent**: Knowledge-based SQL generation, semantic model, query patterns, evaluation
- **pal agent**: LearningMachine (profile + memory + learned knowledge), two-tier storage, MCP research

Into a **Data Agent** that:
1. Searches knowledge before generating SQL (never guesses)
2. Handles data quality issues automatically (type mismatches, date formats)
3. Learns from corrections and successful queries
4. Provides insights, not just data
5. Supports reusable workflows for common analyses

---

## Architecture

```
data_agent/
├── __init__.py                 # Package exports
├── agent.py                    # Main agent with LearningMachine
├── semantic_model.py           # Dynamic schema from knowledge
├── knowledge/
│   ├── tables/                 # Layer 1+2: Table metadata
│   │   └── *.json              # Schema, descriptions, data_quality_notes
│   ├── queries/                # Layer 1: Query patterns
│   │   └── *.sql               # Validated SQL with annotations
│   └── business/               # Layer 2: Business definitions
│       └── metrics.json        # Metric definitions, rules, gotchas
├── tools/
│   ├── __init__.py
│   ├── save_query.py           # Save validated queries → KB
│   ├── analyze.py              # Result analysis (insights)
│   └── introspect.py           # Layer 6: Runtime schema inspection
├── workflows/                  # Reusable analysis templates
│   ├── __init__.py
│   ├── data_validation.py
│   └── metrics_report.py
├── evals/                      # Evaluation harness
│   ├── __init__.py
│   ├── test_cases.py
│   └── run_evals.py
├── scripts/
│   ├── load_data.py
│   └── load_knowledge.py
└── README.md
```

---

## Phase 1: Core Agent

### 1.1 Create `data_agent/agent.py`

**Requirements:**
- Use `OpenAIResponses(id="gpt-4.1")` as the model
- Include `LearningMachine` with all three configs (from pal.py pattern):
  ```python
  learning=LearningMachine(
      knowledge=data_agent_knowledge,
      user_profile=UserProfileConfig(mode=LearningMode.AGENTIC),
      user_memory=UserMemoryConfig(mode=LearningMode.AGENTIC),
      learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
  )
  ```
- Include `SQLTools(db_url=db_url)` for database access
- Include `ReasoningTools(add_instructions=True)` for step-by-step reasoning
- Include custom tools: `save_validated_query`, `analyze_results`, `introspect_schema`
- Optionally include `MCPTools` for Exa research (if EXA_API_KEY is set)
- Set `search_knowledge=True` to always search KB before responding
- Set `add_history_to_context=True` with `num_history_runs=5`

**System message must include:**
1. The semantic model (table descriptions, data quality notes)
2. Clear workflow: search KB → identify tables → check data quality → generate SQL → validate → analyze
3. SQL rules (LIMIT 50, no SELECT *, never destructive)
4. Self-correction instructions (investigate zero rows, type mismatches)
5. Instruction to offer saving successful queries

**Pattern to follow:** Combine `text_to_sql/agent.py` system message with `pal.py` LearningMachine setup.

### 1.2 Create `data_agent/semantic_model.py`

**Requirements:**
- Load table metadata from `knowledge/tables/*.json`
- Load business definitions from `knowledge/business/*.json`
- Build a human-readable summary for the system prompt
- Include data_quality_notes prominently

**Pattern to follow:** Enhance `text_to_sql/semantic_model.py` to include business rules.

### 1.3 Create `data_agent/tools/save_query.py`

**Requirements:**
- Accept: name, question, query, summary, tables_used, data_quality_notes, business_context
- Validate: only SELECT/WITH queries allowed
- Security: check for dangerous keywords
- Store as JSON in knowledge base with `type: "validated_query"`

**Pattern to follow:** Enhance `text_to_sql/tools/save_query.py`.

### 1.4 Create `data_agent/tools/analyze.py`

**Requirements:**
- Accept query results, original question, SQL used, optional context
- Provide:
  - Key findings summary
  - Basic statistics for numeric columns
  - Top results as formatted table
  - Suggested follow-up questions
- Handle empty results with actionable suggestions

**Purpose:** The agent should provide insights, not just data. This is a key differentiator from basic text-to-SQL.

### 1.5 Create `data_agent/tools/introspect.py`

**Requirements:**
- List all tables if no table_name provided
- For specific table: show columns, types, nullable, primary keys, foreign keys, indexes
- Optionally include sample data
- Use SQLAlchemy `inspect()` for metadata

**Purpose:** Layer 6 - Runtime context when KB info is missing or stale.

### 1.6 Create `data_agent/knowledge/business/metrics.json`

**Requirements:**
- Define metrics with: name, definition, table, calculation
- Include business rules as a list
- Include common_gotchas with: issue, tables_affected, solution

**Example metrics for F1 data:**
- Race Win, World Championship, Podium Finish, Fastest Lap, DNF, Points Finish

### 1.7 Copy and organize knowledge files

- Copy `text_to_sql/knowledge/*.json` → `data_agent/knowledge/tables/`
- Copy `text_to_sql/knowledge/common_queries.sql` → `data_agent/knowledge/queries/`

### 1.8 Create scripts

**`data_agent/scripts/load_data.py`:**
- Download F1 CSV files from S3
- Load into PostgreSQL using pandas + sqlalchemy
- Pattern: copy from `text_to_sql/scripts/load_f1_data.py`

**`data_agent/scripts/load_knowledge.py`:**
- Load all files from `knowledge/` directory into the agent's KB
- Pattern: copy from `text_to_sql/scripts/load_knowledge.py`

### 1.9 Create evaluation harness

**`data_agent/evals/test_cases.py`:**
- Define test cases as: (question, expected_values, category)
- Categories: basic, aggregation, data_quality, complex, edge_case
- Pattern: enhance from `text_to_sql/examples/evaluate.py`

**`data_agent/evals/run_evals.py`:**
- Run agent on each test case
- Check if expected values appear in response
- Report pass/fail with timing
- Support filtering by category
- Support verbose mode

---

## Phase 2: Workflows

### 2.1 Create `data_agent/workflows/data_validation.py`

**Purpose:** Validate data quality across tables.

**Steps:**
1. Get table list (all or specified)
2. For each table: row count, null rates, date ranges
3. Check type consistency (position column types)
4. Check referential integrity (driver names match across tables)
5. Report anomalies

**Implementation:** Use Agno's `Workflow` class with `RunEvent` for streaming progress.

### 2.2 Create `data_agent/workflows/metrics_report.py`

**Purpose:** Generate standard reports.

**Report types:**
- `season_summary`: Championships, race stats, notable records for a year
- `driver_profile`: Career overview, year-by-year, best performances
- `team_comparison`: Head-to-head for 2+ teams
- `historical_trends`: Multi-year analysis

**Implementation:** Use Agno's `Workflow` class. Each report type generates a structured prompt for the agent.

---

## Phase 3: Connectors (Future)

### 3.1 Slack MCP Connector
- Access institutional knowledge from Slack channels
- Search for metric definitions, decisions, incidents

### 3.2 Google Docs Connector
- Access documentation, runbooks
- Search for business context

### 3.3 Notion Connector
- Access wikis, glossaries
- Search for definitions, processes

---

## Integration Points

### Register in `app/config.yaml`

Add data_agent to the agents list:
```yaml
agents:
  - name: data-agent
    module: data_agent.agent
    attribute: data_agent
```

### Update `agents/__init__.py`

Export the data_agent:
```python
from data_agent import data_agent
```

---

## Testing Checklist

### Basic Functionality
- [ ] Agent responds to simple questions
- [ ] Agent searches knowledge base before generating SQL
- [ ] Agent handles data quality issues (type mismatches)
- [ ] Agent provides analysis, not just raw data

### Learning Loop
- [ ] Agent can save validated queries
- [ ] Saved queries are retrieved for similar questions
- [ ] LearningMachine captures corrections

### Workflows
- [ ] Data validation workflow runs
- [ ] Metrics report workflow generates reports

### Evaluation
- [ ] All basic test cases pass
- [ ] Aggregation test cases pass
- [ ] Data quality test cases pass

---

## Key Patterns from Existing Code

### From `text_to_sql/agent.py`:
- Knowledge-based approach (search before generate)
- Semantic model in system message
- Data quality notes handling
- SQL rules enforcement

### From `pal.py`:
- LearningMachine with all three configs
- MCP tools integration
- Two-tier storage (agent KB + user data)
- Agentic learning mode

### From `db/`:
- Use `db_url` from `db.url`
- Use `get_postgres_db()` from `db.session`

---

## Success Criteria

The data agent is successful when:

1. **Accuracy**: Passes 90%+ of evaluation test cases
2. **Learning**: Demonstrates improvement on repeated similar questions
3. **Analysis**: Provides insights beyond raw query results
4. **Reliability**: Handles data quality edge cases without failing
5. **Usability**: Works via CLI, API, and workflows

---

## References

- OpenAI Data Agent Article: https://openai.com/index/how-openai-built-its-data-agent/
- Agno Documentation: https://docs.agno.com
- Existing text_to_sql implementation: `text_to_sql/`
- Existing pal implementation: `agents/pal.py`