# service-desk-agent

A thin Flask shell that hosts the **Game Status** dashboard.

`scripts/main.py` is the only entrypoint:
1. Loads the root `.env` (Jira credentials) via `config_loader.apply()`.
2. Dynamically mounts `../game-status-analysis/server.py`'s Blueprint at the
   **root** (`/`) — the dashboard IS the site, no `/game-status` prefix or
   `/dashboard` redirect.

For the `game-status-analysis` Blueprint to load, that sibling directory must be
present alongside `service-desk-agent` (see the workspace-root `CLAUDE.md`).

## Running locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r scripts/requirements.txt
cd scripts
python main.py    # http://localhost:8081
```

## Required `.env` variables

```env
JIRA_DOMAIN=your-tenant.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
```

Never commit `.env`.
