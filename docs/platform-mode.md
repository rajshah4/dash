# Platform Mode (OpenHands)

Platform mode runs Dash on the full OpenHands platform. The standard OpenHands coding agent is extended with Dash's context via auto-loaded skills.

## Why Platform Mode

- Terminal access for `psql` and shell tools
- File editor for knowledge, learnings, and reports
- Python for post-processing and charts
- Browser for rendering outputs
- Docker sandbox for isolation

## Quick Start

```sh
docker compose -f compose.platform.yaml build dash-sandbox  # Once: custom image with psql
docker compose -f compose.platform.yaml up -d
python -m dash.scripts.load_data
open http://localhost:3000   # Configure LLM in Settings, then chat
```

## Skills Injection

Context is delivered via skill files mounted into the OpenHands server:

| Skill | Content |
|-------|---------|
| `skills/dash-agent.md` | Agent identity, DB connection, workflow, insight guidelines |
| `skills/dash-schema.md` | Table metadata, data quality gotchas, SQL rules |
| `skills/dash-sql-patterns.md` | Validated query templates, business rules |

## Custom Sandbox

Dash uses a [custom Docker sandbox](https://docs.openhands.dev/usage/runtimes/docker) with `postgresql-client` pre-installed so the agent can run `psql` commands directly. This is the official OpenHands sandbox model — your repo is mounted into the container and the agent operates in an isolated environment.

## Database Clients (Beyond Postgres)

`psql` is PostgreSQL-only. If you use a different database, install the appropriate client in `Dockerfile.sandbox` and update your skills/instructions accordingly.

- **MySQL/MariaDB**: install `mysql` client (`default-mysql-client` on Debian/Ubuntu).
- **Snowflake**: use `snowsql` or the Python connector.
- **BigQuery**: use the `bq` CLI or Python client.
- **Redshift**: `psql` usually works (Postgres-compatible), but pin versions for stability.
- **Databricks**: use the `databricks` CLI or Python connector.

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
