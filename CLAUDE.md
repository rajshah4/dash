# CLAUDE.md

## Project Overview

Dash is a self-learning data agent that delivers **insights, not just SQL results**. Built on the [OpenHands Software Agent SDK](https://docs.openhands.dev/sdk) and deployable on the [OpenHands Platform](https://docs.openhands.dev). It uses 6 layers of context (inspired by [OpenAI's in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/)) to ground SQL generation and provide meaningful answers.

Two modes: **SDK mode** for lightweight validation and testing; **Platform mode** for the full OpenHands experience (terminal, file editor, sandbox, psql).

## Structure

```
dash/
├── agents.py             # Agent definition (SDK mode)
├── platform.py           # Platform mode launcher (opens browser)
├── mcp_config.example.json # Example MCP server configuration
├── paths.py              # Path constants
├── prompts/
│   ├── system_prompt.j2          # SDK mode system prompt
│   ├── security_policy.j2        # Security policy
│   └── security_risk_assessment.j2 # Risk assessment template
├── knowledge/            # Knowledge files (both modes)
│   ├── tables/           # Table metadata JSON files (Layer 1)
│   ├── business/         # Business rules and metrics (Layer 2)
│   ├── queries/          # Validated SQL queries (Layer 3)
│   └── learnings/        # Persistent discoveries from sessions (Layer 5)
├── context/
│   ├── semantic_model.py # Layer 1: Table usage loader
│   ├── business_rules.py # Layer 2: Business rules loader
│   ├── query_patterns.py # Layer 3: Query patterns loader
│   └── learnings.py      # Layer 5: Persistent learnings loader
├── tools/
│   ├── sql.py            # RunSQLTool — execute read-only SQL
│   ├── introspect.py     # IntrospectSchemaTool — discover tables/columns
│   ├── save_query.py     # SaveValidatedQueryTool — save queries as .sql patterns
│   └── save_learning.py  # SaveLearningTool — save schema quirks/discoveries
├── scripts/
│   ├── load_data.py      # Load F1 sample data
│   ├── load_knowledge.py # Validate knowledge files
│   └── check_schema.py   # Schema drift detection (Layer 1 safety check)
└── evals/
    ├── test_cases.py     # Test cases with golden SQL
    ├── grader.py         # LLM-based response grader
    └── run_evals.py      # Run evaluations

app/
├── main.py               # API entry point (FastAPI) + chat UI
└── static/index.html     # SDK-mode chat UI

skills/                   # Platform mode — auto-loaded into OpenHands agent
├── dash-agent.md         # Agent identity, DB connection, workflow
├── dash-schema.md        # Table metadata, data quality gotchas, SQL rules
└── dash-sql-patterns.md  # Validated SQL templates, business rules

scripts/                  # Top-level repo scripts
├── cloud_api_demo.py     # Programmatic OpenHands Cloud/Server API demo
├── venv_setup.sh         # Create .venv and install dependencies
├── entrypoint.sh         # Docker entrypoint for SDK mode
├── format.sh             # Code formatting (ruff)
└── validate.sh           # Code validation (ruff + mypy)

db/
├── session.py            # SQLAlchemy engine factory
└── url.py                # Database URL builder
```

## Commands

```bash
# Setup
uv sync
source .venv/bin/activate

# SDK Mode
python -m dash                                  # Interactive CLI (persistent sessions)
python -m dash "Who won in 2019?"               # One-shot query
python -m dash --session <uuid>                 # Resume a previous session
python -m dash --no-persist                     # Disable persistence
python -m dash --confirm                        # Enable confirmation for risky actions
python -m dash.agents                           # Test mode (runs sample query)
python -m app.main                              # API server + chat UI → http://localhost:7777

# Platform Mode (full OpenHands with terminal, file editor, sandbox)
docker compose -f compose.platform.yaml build dash-sandbox   # Once: custom image with psql
docker compose -f compose.platform.yaml up -d   # Start OpenHands + DB
open http://localhost:3000                        # Configure LLM in Settings, then chat

# Data & Knowledge
python -m dash.scripts.load_data                # Load F1 sample data
python -m dash.scripts.load_knowledge           # Validate knowledge files
python -m dash.scripts.check_schema             # Check schema drift (knowledge vs live DB)
python -m dash.scripts.check_schema --fix       # Auto-create missing knowledge files

# Evaluations
python -m dash.evals.run_evals                  # Run all evals (string matching)
python -m dash.evals.run_evals -c basic         # Run specific category
python -m dash.evals.run_evals -v               # Verbose mode (show responses)
python -m dash.evals.run_evals -g               # Use LLM grader
python -m dash.evals.run_evals -r               # Compare against golden SQL results
python -m dash.evals.run_evals -g -r -v         # All modes combined
```

## Architecture

Built on the [OpenHands Software Agent SDK](https://docs.openhands.dev/sdk):

| Component | SDK Mode | Platform Mode |
|-----------|----------|---------------|
| Agent | Custom `Agent` with data-agent prompt | OpenHands CodeAct agent + Dash skills |
| LLM | `LLM` (any LiteLLM provider) | Configured via OpenHands Settings UI |
| Tools | `ToolDefinition` (run_sql, introspect, save_query, save_learning) | Built-in bash (psql), file_editor, browser |
| Context | `AgentContext` + `Skill` → prompt injection | `skills/*.md` mounted into `/app/skills/` |
| MCP | `mcp_config` → external tool servers | Same (optional) |
| Condenser | `LLMSummarizingCondenser` | Handled by platform |
| Security | `ConfirmRisky` confirmation policy | Docker sandbox isolation |
| Persistence | `persistence_dir` on disk | Built into OpenHands server |
| Sandbox | N/A (runs locally) | Docker-isolated execution |

### Custom Tools (registered via `register_tool`)

| Tool | Class | Purpose |
|------|-------|---------|
| `run_sql` | `RunSQLTool` | Execute read-only SQL queries |
| `introspect_schema` | `IntrospectSchemaTool` | Discover tables, columns, types |
| `save_validated_query` | `SaveValidatedQueryTool` | Save reusable queries as .sql patterns |
| `save_learning` | `SaveLearningTool` | Save schema quirks, type gotchas, discoveries |

### Self-Learning Loop

The agent improves across sessions via two persistent knowledge tools:

1. **`save_validated_query`** — saves working SQL in the same tagged `.sql` format as curated patterns. These are loaded back into the prompt for future sessions via `dash/context/query_patterns.py`.
2. **`save_learning`** — saves discovered patterns (schema quirks, type gotchas, error fixes) as JSON files. These are loaded into the prompt via `dash/context/learnings.py`.

Both are loaded at startup and injected as a `Skill` into the agent's context. The condenser further preserves important context within a single session.

### Schema Drift Detection

Run `python -m dash.scripts.check_schema` to compare `knowledge/tables/*.json` against the live database. Detects:
- Tables in knowledge but missing from DB
- New tables in DB without knowledge files
- Column additions/removals
- Type mismatches (with fuzzy matching)

Use `--fix` to auto-generate knowledge files for new tables.

### Condenser

When conversations exceed 100 events, `LLMSummarizingCondenser` compresses older messages into a summary while preserving the system prompt and first user message. This keeps the agent within token limits during long analytical sessions without losing important context (e.g., discovered schema quirks).

### Security Policy

`ConfirmRisky` pauses execution and prompts for user confirmation when the LLM predicts a HIGH-risk action. Since Dash runs read-only SQL, this is mainly a safety net for the `save_validated_query` tool. Enable in CLI with `--confirm` or in the API with `DASH_ENABLE_CONFIRMATION=true`.

### Persistence

Conversations are saved to `.dash_sessions/` by default. In the CLI, each session gets a UUID printed on startup — pass it with `--session <uuid>` to resume. The API automatically persists all sessions and accepts `session_id` in the request body.

## The Six Layers of Context

| Layer | SDK Mode | Platform Mode |
|-------|----------|---------------|
| 1. Table Usage | `knowledge/tables/*.json` → `context/semantic_model.py` | `skills/dash-schema.md` |
| 2. Human Annotations | `knowledge/business/*.json` → `context/business_rules.py` | `skills/dash-sql-patterns.md` |
| 3. Query Patterns | `knowledge/queries/*.sql` → `context/query_patterns.py` | `skills/dash-sql-patterns.md` |
| 4. Institutional Knowledge | MCP connectors (optional) | MCP or `psql` + Python |
| 5. Learnings | `save_learning` tool → `knowledge/learnings/*.json` | Agent saves to `knowledge/` via file editor |
| 6. Runtime Context | `introspect_schema` tool | `psql -c "\d table_name"` |

**SDK Mode**: Layers 1-3 and 5 loaded at startup into agent's `Skill` context. Layer 4 via MCP. Layer 6 via tool.

**Platform Mode**: Layers 1-3 delivered via skill files auto-injected into every conversation. Layers 4-6 via terminal tools.

## Data Quality (F1 Dataset)

| Issue | Solution |
|-------|----------|
| `position` is TEXT in `drivers_championship` | Use `position = '1'` |
| `position` is INTEGER in `constructors_championship` | Use `position = 1` |
| `date` is TEXT in `race_wins` | Use `TO_DATE(date, 'DD Mon YYYY')` |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_API_KEY` | Yes | API key for your LLM provider |
| `LLM_MODEL` | No | Model name (default: `openai/gpt-4.1`) |
| `LLM_BASE_URL` | No | Custom API base URL |
| `LMNR_PROJECT_API_KEY` | No | Laminar API key for tracing (auto-enabled) |
| `DASH_MCP_CONFIG` | No | MCP config as inline JSON string |
| `DASH_MCP_CONFIG_FILE` | No | Path to MCP config JSON file |
| `DASH_PERSISTENCE_DIR` | No | Custom persistence directory (API) |
| `DASH_ENABLE_CONFIRMATION` | No | Enable security confirmation (API) |
| `DASH_CHAT_TIMEOUT` | No | Request timeout in seconds (default: 300) |
| `DASH_MAX_SESSIONS` | No | Max in-memory sessions (default: 100) |
| `DASH_SESSION_TTL` | No | Session TTL in seconds (default: 3600) |
| `DB_*` | No | Database config (defaults: ai/ai/ai) |
