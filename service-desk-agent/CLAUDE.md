# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A thin Flask shell that hosts the Game Status dashboard. `scripts/main.py` is the
only entrypoint: it loads the root `.env` + this component's `config.toml` via
`config_loader.apply()`, dynamically mounts `game-status-analysis/server.py`'s
Blueprint at `/game-status`, and redirects `/dashboard` to `/game-status/`.

There is no AI/Jira-automation logic here anymore — this used to also host a
Gemini-based triage agent (`/triage`, `/scan`, `/rewrite`, `/summarise`, `/detect`),
which has been removed. If you're looking for that, it's gone; don't re-add it
without being asked.

## Running the server

```bash
cd scripts
source venv/bin/activate
python main.py         # starts Flask on port 8080 → /dashboard, /game-status/
```

## Module responsibilities

- `main.py` — Flask app, `importlib`-mounts `game-status-analysis/server.py`'s Blueprint, `/dashboard` redirect

## Required `.env` variables

Jira credentials are shared from the root `.env` via `config_loader.py` — see
`game-status-analysis/CLAUDE.md` for what it actually reads (`JIRA_DOMAIN`,
`JIRA_EMAIL`, `JIRA_API_TOKEN`).
