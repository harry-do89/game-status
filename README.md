# PACT Engineering Suite

A single Jira-tenant (`vvortech.atlassian.net`) analytics + automation suite: one
**AI triage agent** plus **four read-only dashboards** (SUP, Verticals, Production
Incident, Recurring Issues), all served by one Flask process on port **8080** and
exposed via an optional Cloudflare tunnel.

Open `http://localhost:8080/dashboard` — a tab bar of the four boards.

> Architecture & per-project detail: see [`CLAUDE.md`](CLAUDE.md) and each
> sub-project's own `CLAUDE.md`.

## Prerequisites

- Docker + Docker Compose v2 (`docker compose version`)
- Credentials & config:
  - **`.env`** at the repo root — **required**, gitignored. Holds **all secrets**:
    Jira creds (`JIRA_DOMAIN`/`JIRA_EMAIL`/`JIRA_API_TOKEN`), `AGENT_KEY`, webhook URLs,
    Google creds path. Copy `.env.example` → `.env` and fill in.
  - **`<component>/config.toml`** — committed, **non-secret** per-board settings
    (project key / board list / maintain parents+labels / agent mode). Edit in place.
  - `service-desk-agent/credentials/<gcp-sa>.json` — optional (Gemini/AI features).

## Deploy (one command)

```bash
./deploy.sh
```

This runs preflight checks, stops any running stack, builds the image (installing
every board's deps and pre-rendering its data via `build.sh`), and starts the
container detached. When it finishes:

```
Dashboard: http://localhost:8080/dashboard
Logs:      docker compose logs -f all-in-one
```

Flags:

| Command | Effect |
|---|---|
| `./deploy.sh` | preflight → `down` → `build` → `up -d` |
| `./deploy.sh --no-cache` | force a clean image rebuild |
| `./deploy.sh --logs` | tail container logs after starting |

To expose it publicly, uncomment the `cloudflared` service in
`docker-compose.yml` and re-run `./deploy.sh`.

## Adding a new board

The `Dockerfile` is board-agnostic — you never edit it. To add a board:

1. Create the board folder following the existing pipeline pattern (an extractor in
   `script/`, a generator in `scratch/`, a `server.py` Blueprint, a `requirements.txt`,
   and a `config.toml` for its non-secret settings). Load config at the top of the
   extractor/generator:
   ```python
   sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
   import config_loader; config_loader.apply(__file__)
   ```
2. Mount its Blueprint and add a dashboard tab in
   `service-desk-agent/scripts/main.py` (copy an existing block, e.g. `/maintain`).
3. Append **one line** to [`build.sh`](build.sh):
   ```bash
   build_board <board-dir> script/<x>_extractor.py scratch/generate_<x>_html.py
   ```
4. `./deploy.sh` — done. The build log shows `=== building board: <board-dir> ===`.

## Local development (no Docker)

```bash
# The whole app:
cd service-desk-agent/scripts && python main.py     # :8080 → /dashboard

# One board standalone:
cd <board>-analysis && python server.py             # :5000

# Regenerate a board's data:
cd <board>-analysis
python script/<x>_extractor.py        # → result/<x>_tickets_export.csv
python scratch/generate_<x>_html.py   # → result/<x>_visual_report.html
```

## Tests

Each project has its own suite: `cd <project> && python3 -m pytest`.
