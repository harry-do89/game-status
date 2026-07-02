# AGENTS.md — Workspace Overview

Top-down map of this workspace so you can work effectively **without reading every
sub-project**. Each sub-project has its own detailed `AGENTS.md` — open that only
when you actually touch that project.

## What this workspace is

A single Jira tenant (`vvortech.atlassian.net`) analytics suite for an
online-gaming engineering org. It has **one read-only analytics dashboard**
("Game Status"), served by a thin Flask shell (see `docker-compose.yml`).

```
                         ┌─────────────────────────────────────────────┐
                         │  service-desk-agent (Flask, port 8081)        │
                         │  scripts/main.py = the ONE entrypoint         │
                         │                                               │
                         │  /                 → game-status-analysis     │
                         │                       (served directly, no    │
                         │                        prefix/redirect)       │
                         └─────────────────────────────────────────────┘
                                             │
                                      Jira REST API v3
```

## The two sub-projects

| Folder | Role | Mount | Entry to read its AGENTS.md when… |
|---|---|---|---|
| `service-desk-agent/` | Thin Flask shell that mounts and serves the dashboard. | serves `:8081` | touching the Flask host or mount logic |
| `game-status-analysis/` | "Game Status" SVG flow graph across 5 spaces (ID/GAME/CER/LOC/RM); node = status w/ live count, click → ticket list | `/` (root) | changing Game Status flow/layout |

### Game Status timeline note

`game-status-analysis` has one extra live API beyond the standard dashboard
refresh/status routes: `GET /api/ticket/<GAME-key>/timeline`.

- It is used by the shared ticket timeline modal (`shared/timeline_modal.py`).
- Top-level GAME stages in that modal are **not** built from Jira changelog anymore.
  They are read directly from issue custom fields whose display names are resolved at
  runtime via Jira `GET /rest/api/3/field`.
- Current field-backed stages are:
  `Math`, `Contract Alignment`, `Development`, `Integration QC`, `Optimization`.
- For each of those stages, the server reads three fields from the GAME issue:
  `ETA (...)`, `Actual Start (...)`, `Actual End (...)`.
- `Planned` and `Done` are intentionally hidden from the timeline response.
- `Packaging` stays visible in the response/UI but currently has no field mapping yet,
  so it will return null dates until matching Jira fields are added.
- Development sub-stages (`BE`/`BO`/`Platform`/`FE`/`Math`/`VOR`) still come from the
  extractor cache file `result/game_status_substages.json`, not from the top-level
  issue fields.

## The Game Status dashboard pipeline

1. **Extract** — `script/game_status_extractor.py` hits the Jira API (`POST /rest/api/3/search/jql`,
   cursor pagination via `nextPageToken`) → writes a CSV in `result/`.
2. **Visualize** — `scratch/generate_game_status_html.py` reads that CSV, computes metrics,
   writes a **self-contained** HTML file in `result/`.
   Pure, testable logic lives in `scratch/report_logic.py` — never inlined.
3. **Serve** — `server.py` exports a Flask **Blueprint** with 4 routes:
   `GET /` (serves the HTML, `no-cache`), `POST /api/refresh` (incremental),
   `POST /api/refresh/full` (full), `GET /api/status`. `main.py` mounts the
   Blueprint at the **root** (`/`) via `importlib` — no `/game-status` prefix.

**Refresh buttons** (on the board): two floating buttons run the pipeline in a
background thread, calling `/api/refresh`/`/api/refresh/full` directly (no
prefix detection needed — the blueprint is always mounted at root). They then
poll `/api/status` until `running:false` and reload. Cooldowns persist in
`localStorage` with a `gs_` key prefix.

**Conventions:**
- "Resolved/Done" statuses + an **effective resolved date** fallback chain
  (`Resolved Date` → `Status Category Change Date` → `Updated Date`).
- Working-hours math and ISO-week bucketing helpers in `report_logic.py`.
- `server.py` forces `game-status-analysis`'s own `.env` creds into the subprocess
  so the agent's Jira creds don't leak across tenants/projects.
- Incremental fetch via `SINCE_DATE` env → `AND updated >= "..."`, upsert by key.

## service-desk-agent in one paragraph

`main.py` is the only entrypoint. It loads the root `.env` + its own
`config_loader.apply()`, dynamically mounts `game-status-analysis/server.py`'s
Blueprint at the **root** (`/`) via `importlib` — the dashboard IS the site,
no `/game-status` prefix or `/dashboard` redirect. There's no AI/Jira-automation
logic here; a prior Gemini-based triage agent that used to live in this Flask
process has been removed. Full detail: `service-desk-agent/AGENTS.md`.

## Configuration (one `.env` + per-component `config.toml`)

- **Root `.env`** (gitignored) — **all secrets**: Jira creds
  (`JIRA_DOMAIN`/`JIRA_EMAIL`/`JIRA_API_TOKEN`). Single source for every component.
- **`<component>/config.toml`** (committed) — that board's **non-secret**
  behaviour: `project_key`, etc.
- **`config_loader.py`** (repo root) — every extractor / generator / `main.py` calls
  `config_loader.apply(__file__)` at startup. It loads the root `.env` and the caller's
  own `config.toml`, then maps values onto the env var names the code already reads
  (`JIRA_PROJECT_KEY`, and derives `JIRA_BASE_URL`/`JIRA_USER_EMAIL` from the
  creds). Reads are unchanged; only the source moved.

## Run it

```bash
# Local (the whole thing):
cd service-desk-agent/scripts && python main.py    # http://localhost:8081

# Game Status standalone (dev):
cd game-status-analysis && python server.py        # :5000

# Regenerate the board's data:
cd game-status-analysis
python script/game_status_extractor.py        # → result/game_status_tickets_export.csv
python scratch/generate_game_status_html.py    # → result/game_status_visual_report.html
```

## Deploy

**One command:** `./deploy.sh` — preflight (Docker daemon, `.env`), then
`docker compose down → build → up -d`, then prints the dashboard URL.
Flags: `--no-cache` (clean rebuild), `--logs` (tail logs after start). See
`README.md` for the full walkthrough.

How it fits together:
- **`build.sh`** (repo root) — the board manifest. One `build_board <dir> <extractor>
  <generator>` line per board; it installs that board's `requirements.txt` and
  pre-renders its data. **Adding a board = append one line here.**
- **`Dockerfile`** — `COPY . .` → install Flask-shell deps → `RUN bash build.sh` →
  `CMD python3 scripts/main.py`. It never needs editing when boards are added.
- **`.dockerignore`** — keeps `.venv/`, `venv/`, `__pycache__/`, `.git/`, `result/`
  out of the build context. **Must not** exclude `.env` — build-time extractors need
  each board's creds (carried in by `COPY . .`).
- **`docker-compose.yml`** — runs the `all-in-one` app (host networking) + an
  optional `cloudflared` tunnel.
- Every board, plus the Flask shell, reads Jira creds from the single root
  gitignored `.env` (the compose `env_file`).

## Hard rules (apply everywhere)

- **Never commit** `.env` or `credentials.json` (gitignored per project). Never echo
  secrets into the repo.
- **Never delete or overwrite files in any `result/` directory** — they hold live
  generated data; regenerate via the pipeline instead of hand-editing.
- Jira: always `POST /rest/api/3/search/jql` (GET search is deprecated); paginate via
  `nextPageToken`; `timeout=30`; `time.sleep(0.5)` between pages.
- Do **not** add `Co-Authored-By` trailers to commits (repo convention).
- Keep pure logic in `report_logic.py`; keep the async-202 pattern in the agent.
