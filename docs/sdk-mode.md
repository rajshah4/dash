# SDK Mode

SDK mode runs Dash locally using the OpenHands SDK. This is the lightweight option for quick iteration, testing, and evaluation without the full OpenHands UI.

## Quick Start

```sh
docker compose up -d dash-db
python -m dash.scripts.load_data
python -m app.main       # → http://localhost:7777 (chat UI + API)
python -m dash           # Interactive CLI
```

## What You Get

- Custom SQL tools (`run_sql`, `introspect_schema`, `save_validated_query`, `save_learning`)
- FastAPI server + built-in chat UI
- Local persistence (`.dash_sessions/`)
- Local evaluation harness

## When to Use SDK Mode

- Prototyping prompts and tools
- Writing and validating knowledge files
- Running evals before deploying to the platform
