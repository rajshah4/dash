# Dash

Dash is a **self-learning data agent** that grounds its answers in **6 layers of context** and improves with every run. Built on the [OpenHands Software Agent SDK](https://docs.openhands.dev/sdk) and deployable on the [OpenHands Platform](https://docs.openhands.dev).

Inspired by [OpenAI's in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/).

## Quick Start

### SDK Mode (fastest)

```sh
git clone https://github.com/rajshah4/dash.git && cd dash
cp example.env .env          # Add your LLM API key
docker compose up -d dash-db
./scripts/venv_setup.sh && source .venv/bin/activate
python -m dash.scripts.load_data
python -m dash               # Interactive CLI
```

### Platform Mode (full OpenHands UI)

```sh
git clone https://github.com/rajshah4/dash.git && cd dash
cp example.env .env
docker compose -f compose.platform.yaml build dash-sandbox  # Custom sandbox with psql
docker compose -f compose.platform.yaml up -d
python -m dash.scripts.load_data
open http://localhost:3000    # Configure your LLM in Settings, then chat
```

**Try it** (sample F1 dataset):

- Who won the most F1 World Championships?
- How many races has Lewis Hamilton won?
- Compare Ferrari vs Mercedes points 2015-2020

## Why Text-to-SQL Breaks in Practice

Our goal is simple: ask a question in English, get a correct, meaningful answer. But raw LLMs writing SQL hit a wall fast:

- **Schemas lack meaning.**
- **Types are misleading.**
- **Tribal knowledge is missing.**
- **No way to learn from mistakes.**
- **Results generally lack interpretation.**

The root cause is missing context and missing memory.

Dash solves this with **6 layers of grounded context**, a **self-learning loop** that improves with every query, and a focus on **understanding your question** to deliver insights you can act on.

## The Six Layers of Context

This architecture follows [OpenAI's approach to building their in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/). Each layer adds context that makes SQL generation more reliable:

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

### Schema Drift Detection

```sh
python -m dash.scripts.check_schema          # compare knowledge vs live DB
python -m dash.scripts.check_schema --fix    # auto-create missing knowledge files
```

## Insights, Not Just Rows

Dash reasons about what makes an answer useful, not just technically correct.

**Question:**
Who won the most races in 2019?

| Typical SQL Agent | Dash |
|------------------|------|
| `Hamilton: 11` | Lewis Hamilton dominated 2019 with **11 wins out of 21 races**, more than double Bottas's 4 wins. This performance secured his sixth world championship. |

## Two Modes

Dash supports two deployment modes — use SDK mode for quick iteration and testing, Platform mode for the full experience:

### SDK Mode (Lightweight)

Standalone deployment with custom SQL tools, a FastAPI API, and a built-in chat UI. Great for validating queries and evaluating agent performance.

```sh
docker compose up -d dash-db
python -m dash.scripts.load_data
python -m app.main       # → http://localhost:7777 (chat UI + API)
python -m dash           # Interactive CLI
```

The 6 layers are loaded directly into the agent's prompt. Custom tools handle SQL execution, schema introspection, and knowledge persistence.

### Platform Mode (Full OpenHands)

Run Dash on the [OpenHands platform](https://docs.openhands.dev). The standard OpenHands coding agent is extended with Dash's 6 layers of context via **auto-loaded skills**.

**The idea: a coding agent that already knows your database.**

- 🖥️ **Terminal** — `psql` pre-installed in the sandbox for formatted tabular output
- 📝 **File Editor** — browse knowledge files, save reports and learnings
- 🐍 **Python** — go beyond SQL with pandas, scipy, matplotlib for charts and stats
- 🌐 **Browser** — preview generated visualizations
- 🔒 **Sandbox** — all execution runs in an isolated Docker container

```sh
docker compose -f compose.platform.yaml build dash-sandbox  # Once: custom sandbox with psql
docker compose -f compose.platform.yaml up -d
python -m dash.scripts.load_data
open http://localhost:3000   # Configure LLM in Settings, then chat
```

Context is delivered via three skill files mounted into the OpenHands server:

| Skill | Content |
|-------|---------|
| `skills/dash-agent.md` | Agent identity, DB connection, workflow, insight guidelines |
| `skills/dash-schema.md` | Table metadata, data quality gotchas, SQL rules |
| `skills/dash-sql-patterns.md` | Validated query templates, business rules |

## How It Works

Dash is built on the [OpenHands Software Agent SDK](https://docs.openhands.dev/sdk):

| Component | SDK Mode | Platform Mode |
|-----------|----------|---------------|
| **Agent** | Custom `Agent` with data-agent system prompt | OpenHands CodeAct agent + Dash skills |
| **Tools** | `run_sql`, `introspect_schema`, `save_validated_query`, `save_learning` | Built-in `bash` (psql), `file_editor`, `browser` |
| **Context Injection** | Layers loaded as `Skill` + `AgentContext` | Skills mounted into `/app/skills/` (auto-loaded) |
| **MCP** | External tool servers via [Model Context Protocol](https://modelcontextprotocol.io/) | Same (optional) |
| **Condenser** | `LLMSummarizingCondenser` compresses long conversations | Handled by platform |
| **Security** | `ConfirmRisky` confirmation for destructive actions | Sandbox isolation |
| **Persistence** | Save/resume conversations to disk | Built into OpenHands server |
| **Tracing** | [Laminar](https://www.lmnr.ai) (auto-enabled with `LMNR_PROJECT_API_KEY`) | Same |
| **Sandbox** | N/A (runs locally) | Docker-isolated execution |

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

## Local Development

```sh
# Setup
./scripts/venv_setup.sh && source .venv/bin/activate
docker compose up -d dash-db
python -m dash.scripts.load_data

# SDK Mode
python -m dash                          # Interactive CLI
python -m dash "Who won in 2019?"       # One-shot query
python -m app.main                      # API server + chat UI → http://localhost:7777

# Platform Mode
docker compose -f compose.platform.yaml build dash-sandbox   # Once
docker compose -f compose.platform.yaml up -d
open http://localhost:3000              # Configure LLM in Settings, then chat

# Evals (SDK mode)
python -m dash.evals.run_evals              # String matching
python -m dash.evals.run_evals -g           # LLM grader
python -m dash.evals.run_evals -g -r -v     # Full evaluation

# Schema drift check
python -m dash.scripts.check_schema          # Detect knowledge vs DB mismatches
python -m dash.scripts.check_schema --fix    # Auto-generate missing knowledge files
```

## OpenHands Cloud

Dash works with [OpenHands Cloud](https://docs.openhands.dev/openhands/usage/cloud/cloud-ui) for managed deployments — no Docker, no self-hosting.

### Setup

1. **Create an API key** — Go to [Settings → API Keys](https://docs.openhands.dev/openhands/usage/settings/api-keys-settings) and generate an OpenHands API Key.
2. **Configure your LLM** — In [Settings → LLM](https://docs.openhands.dev/openhands/usage/settings/llm-settings), choose a provider and enter your API key. OpenHands supports bring-your-own-key (BYOK) for OpenAI, Anthropic, Azure, and others, or you can use the built-in OpenHands LLM key.
3. **Connect your repo** — Link your GitHub/GitLab/Bitbucket repository. Dash's `skills/` directory and knowledge files will be available to the agent automatically.
4. **Store secrets** — Use the [Secrets tab](https://docs.openhands.dev/openhands/usage/cloud/cloud-ui) to store `DB_HOST`, `DB_PASS`, and other credentials instead of `.env` files.
5. **Set a budget** — Use the per-conversation budget limit for cost governance.

### Programmatic Access (Cloud API)

Use the [Cloud API](https://docs.openhands.dev/openhands/usage/cloud/cloud-api) to run data tasks in CI/CD pipelines or scheduled jobs:

```sh
# Run a data quality audit via the API
OPENHANDS_HOST=https://app.openhands.ai \
OPENHANDS_API_KEY=oh-... \
python scripts/cloud_api_demo.py "Run a data quality audit on all tables"
```

See [`scripts/cloud_api_demo.py`](scripts/cloud_api_demo.py) for a full example that creates a conversation, sends a message, and polls for results.

### MCP for Enterprise Data Sources

The [Model Context Protocol](https://docs.openhands.dev/overview/model-context-protocol) (MCP) connects Dash to external data systems — data catalogs, BI tools, Slack, GitHub, and more. MCP works across SDK mode, self-hosted platform, and Cloud.

```json
{
  "mcpServers": {
    "postgres": {
      "command": "uvx",
      "args": ["mcp-server-postgres"],
      "env": { "POSTGRES_CONNECTION_STRING": "postgresql://..." }
    },
    "slack": {
      "command": "uvx",
      "args": ["mcp-server-slack"],
      "env": { "SLACK_BOT_TOKEN": "xoxb-..." }
    }
  }
}
```

See [`dash/mcp_config.example.json`](dash/mcp_config.example.json) for more examples (filesystem, GitHub, fetch).

### Enterprise Integrations

OpenHands Cloud also supports:
- **Repository integrations** — GitHub, GitLab, Bitbucket (auto-load skills from your repo)
- **Slack app** — Chat with your data agent from Slack
- **Budget limits** — Per-conversation cost caps for governance

## Custom Sandbox

Dash uses a [custom Docker sandbox](https://docs.openhands.dev/usage/runtimes/docker) with `postgresql-client` pre-installed so the agent can run `psql` commands directly. This is the official OpenHands sandbox model — your repo is mounted into the container and the agent operates in an isolated environment.

To customize the sandbox (e.g., add Python data science libraries):

```dockerfile
# Dockerfile.sandbox
FROM docker.openhands.dev/openhands/openhands-agent-server:latest
RUN apt-get update && apt-get install -y postgresql-client python3-pandas
```

Build and use it:

```sh
docker compose -f compose.platform.yaml build dash-sandbox
docker compose -f compose.platform.yaml up -d
```

The custom image is referenced in `compose.platform.yaml` via `AGENT_SERVER_IMAGE_REPOSITORY` and `AGENT_SERVER_IMAGE_TAG`.

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
| `OPENHANDS_HOST` | No | OpenHands server URL for platform mode (default: `http://localhost:3000`) |
| `OPENHANDS_API_KEY` | No | API key for the OpenHands server (platform mode) |
| `DB_*` | No | Database config (defaults to `ai`/`ai`/`ai` on localhost) |

## Deploy with Docker

```sh
# SDK Mode — DB + API with built-in chat UI
docker compose up -d --build
docker exec -it dash-api python -m dash.scripts.load_data
# → http://localhost:8000

# Platform Mode — Full OpenHands with terminal, file editor, sandbox
docker compose -f compose.platform.yaml build dash-sandbox  # Once: custom image with psql
docker compose -f compose.platform.yaml up -d
python -m dash.scripts.load_data
# → http://localhost:3000 (configure LLM in Settings first)
```

## Acknowledgements

This repo is based on [agno-agi/dash](https://github.com/agno-agi/dash) by [Ashpreet Bedi](https://www.ashpreetbedi.com), refactored to use the [OpenHands Software Agent SDK](https://docs.openhands.dev/sdk) and the [OpenHands Platform](https://docs.openhands.dev). The 6-layer context architecture is inspired by [OpenAI's in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/). The platform integration extends OpenHands's coding agent with domain-specific skills for data work.

## Further Reading

- [OpenAI's In-House Data Agent](https://openai.com/index/inside-our-in-house-data-agent/) — the inspiration
- [Self-Improving SQL Agent](https://www.ashpreetbedi.com/articles/sql-agent) — deep dive on an earlier architecture
- [agno-agi/dash](https://github.com/agno-agi/dash) — the original Agno implementation
- [OpenHands SDK Docs](https://docs.openhands.dev/sdk) — the framework Dash is built on
