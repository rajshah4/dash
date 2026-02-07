# OpenHands Cloud and Enterprise Fit

## OpenHands Cloud

Dash works with [OpenHands Cloud](https://docs.openhands.dev/openhands/usage/cloud/cloud-ui) for managed deployments — no Docker, no self-hosting.

### Cloud vs Self-Hosted

OpenHands can run as managed Cloud or as a self-hosted server in your own infrastructure. Use Cloud for faster onboarding and reduced ops. Use self-hosted when you need tighter network control, data residency guarantees, or custom security policies.

### Setup

1. **Create an API key** — Go to [Settings → API Keys](https://docs.openhands.dev/openhands/usage/settings/api-keys-settings) and generate an OpenHands API Key.
2. **Configure your LLM** — In [Settings → LLM](https://docs.openhands.dev/openhands/usage/settings/llm-settings), choose a provider and enter your API key. OpenHands supports bring-your-own-key (BYOK) for OpenAI, Anthropic, Azure, and others, or you can use the built-in OpenHands LLM key.
3. **Connect your repo** — Link your GitHub/GitLab/Bitbucket repository. Dash's `skills/` directory and knowledge files will be available to the agent automatically.
4. **Store secrets** — Use the [Secrets tab](https://docs.openhands.dev/openhands/usage/cloud/cloud-ui) to store `DB_HOST`, `DB_PASS`, and other credentials instead of `.env` files.
5. **Set a budget** — Use the per-conversation budget limit for cost governance.

## Programmatic Access (Cloud API)

Use the [Cloud API](https://docs.openhands.dev/openhands/usage/cloud/cloud-api) to run data tasks in CI/CD pipelines or scheduled jobs:

```sh
# Run a data quality audit via the API
OPENHANDS_HOST=https://app.openhands.ai \
OPENHANDS_API_KEY=oh-... \
python scripts/cloud_api_demo.py "Run a data quality audit on all tables"
```

See `scripts/cloud_api_demo.py` for a full example that creates a conversation, sends a message, and polls for results.

For self-hosted deployments, the same API is available — set `OPENHANDS_HOST` to your internal OpenHands URL. Authentication is optional unless you enable it on your server.

## MCP for Enterprise Data Sources

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

See `dash/mcp_config.example.json` for more examples (filesystem, GitHub, fetch).

## Enterprise Integrations

OpenHands Cloud also supports:

- **Repository integrations** — GitHub, GitLab, Bitbucket (auto-load skills from your repo)
- **Slack app** — Chat with your data agent from Slack
- **Budget limits** — Per-conversation cost caps for governance

## Extensibility and Multi-Agent Deployment

Dash is a template for data agents, not a fixed product. The intended workflow is to customize it to your environment and then deploy multiple specialized agents as your org grows.

### Customization Patterns

- **Per-dataset specialization** — clone the repo and swap `knowledge/` and `skills/` for each data domain (e.g., sales, marketing, finance).
- **Per-team workflows** — adjust tools or prompts to match how each team works (SQL-only vs SQL+Python).
- **MCP toolchains** — connect different internal systems per agent (catalogs, BI, ticketing, docs).
- **Runtime policy** — enable confirmations, timeouts, and budgets based on risk and cost profile.

### Why Multi-Agent Makes Sense

Enterprises rarely have a single schema or workflow. Running multiple smaller agents keeps context tight, improves accuracy, and reduces prompt bloat. It also supports **least-privilege** access — different agents can use different credentials or datasets to limit exposure of sensitive data.
