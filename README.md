# Dash

Dash is a **self-learning data agent** that grounds its answers in **6 layers of context** and improves with every run. Built on the [OpenHands Software Agent SDK](https://docs.openhands.dev/sdk) and deployable on the [OpenHands Platform](https://docs.openhands.dev).

Inspired by [OpenAI's in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/).

## Why Text-to-SQL Breaks in Practice

Our goal is simple: ask a question in English, get a correct, meaningful answer. But raw LLMs writing SQL hit a wall fast:

- **Schemas lack meaning.**
- **Types are misleading.**
- **Tribal knowledge is missing.**
- **No way to learn from mistakes.**
- **Results generally lack interpretation.**

The root cause is missing context and missing memory.

Dash solves this with **6 layers of grounded context**, a **self-learning loop** that improves with every query, and a focus on **understanding your question** to deliver insights you can act on.

## Why OpenHands + Dash Works

- **Real execution, not just generation** — the agent runs `psql`, Python, and shell tools in a sandbox so answers are verifiable.
- **Persistent, auditable workflows** — conversations and artifacts are saved for reproducibility and compliance.
- **Extensible context (MCP)** — connect catalogs, BI tools, and internal systems to ground answers.
- **Enterprise governance** — API keys, secrets, and budget limits for control.
- **Git-native knowledge** — keep `skills/` and `knowledge/` in Git for review, audit, and rollback.
- **Deploy anywhere** — OpenHands Cloud for managed teams or self-hosted for strict data residency.

Dash is meant to be customized — swap in your schema, business rules, query patterns, and tools to fit your data stack. As you scale, it’s common to run multiple specialized agents with **separate access scopes** (different credentials, datasets, or environments) to keep permissions tight and limit blast radius.

See `docs/enterprise.md` for the full cloud + enterprise story.

## Approach: Knowledge + Learning

Dash improves without retraining through **curated knowledge** and **persistent learnings**. The six-layer context model and self-learning loop are documented in `docs/knowledge.md`.

**Example (insights over rows):**

| Typical SQL Agent | Dash |
|------------------|------|
| `Hamilton: 11` | Lewis Hamilton dominated 2019 with **11 wins out of 21 races**, more than double Bottas's 4 wins. This performance secured his sixth world championship. |

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

## Modes

Choose **SDK mode** for fast local iteration and evals, or **Platform mode** for the full OpenHands UI and sandboxed tooling.

See `docs/sdk-mode.md` and `docs/platform-mode.md` for setup details and workflows.

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

## Project Structure (Key Paths)

```
app/                   # FastAPI API + chat UI (SDK mode)
dash/                  # SDK agent, tools, context loaders, evals
  knowledge/           # Curated knowledge + discovered learnings
  scripts/             # Data loading, knowledge validation, schema checks
  evals/               # Test cases, grader, evaluation runner
skills/                # Platform mode skills (auto-loaded by OpenHands)
scripts/               # Repo-level scripts (cloud API demo, setup, formatting)
docs/                  # Detailed documentation (modes, knowledge, evals, enterprise)
```

For the full knowledge system (examples, schema drift checks, and learnings), see `docs/knowledge.md`.

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

# Evals and knowledge validation
python -m dash.evals.run_evals               # See docs/evals.md for options
python -m dash.scripts.load_knowledge        # Validate knowledge files
python -m dash.scripts.check_schema          # Schema drift detection
```

## OpenHands Cloud and Enterprise

Managed deployments, Cloud API, MCP integrations, and enterprise governance are documented in `docs/enterprise.md`.

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

## Docs

- `docs/sdk-mode.md` — SDK mode setup and workflow
- `docs/enterprise.md` — OpenHands Cloud, Cloud API, MCP, enterprise integrations
- `docs/platform-mode.md` — Platform mode setup, skills injection, sandbox
- `docs/knowledge.md` — Six layers, learnings, schema drift, knowledge examples
- `docs/evals.md` — Evaluation harness and grading options

## Acknowledgements

This repo is based on [agno-agi/dash](https://github.com/agno-agi/dash) by [Ashpreet Bedi](https://www.ashpreetbedi.com), refactored to use the [OpenHands Software Agent SDK](https://docs.openhands.dev/sdk) and the [OpenHands Platform](https://docs.openhands.dev). The 6-layer context architecture is inspired by [OpenAI's in-house data agent](https://openai.com/index/inside-our-in-house-data-agent/). The platform integration extends OpenHands's coding agent with domain-specific skills for data work.

## Further Reading

- [OpenAI's In-House Data Agent](https://openai.com/index/inside-our-in-house-data-agent/) — the inspiration
- [Self-Improving SQL Agent](https://www.ashpreetbedi.com/articles/sql-agent) — deep dive on an earlier architecture
- [agno-agi/dash](https://github.com/agno-agi/dash) — the original Agno implementation
- [OpenHands SDK Docs](https://docs.openhands.dev/sdk) — the framework Dash is built on
