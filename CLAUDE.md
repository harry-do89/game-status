# CLAUDE.md — Workspace Overview

Top-down map of this workspace so you can work effectively **without reading every
sub-project**. Each sub-project has its own detailed `CLAUDE.md` — open that only
when you actually touch that project.

## What this workspace is

A single Jira tenant (`vvortech.atlassian.net`) analytics + automation suite for an
online-gaming engineering org. It has **one AI agent** plus **four read-only
analytics dashboards**, all served by one Flask process and exposed publicly via a
Cloudflare tunnel (see `docker-compose.yml`).

```
                         ┌─────────────────────────────────────────────┐
 Jira Automation ──────▶ │  service-desk-agent (Flask, port 8080)        │
 (webhooks)              │  scripts/main.py = the ONE entrypoint         │
                         │                                               │
                         │  AI agent routes:  /triage /scan /rewrite     │
                         │                    /summarise /detect /admin  │
                         │                                               │
                         │  /dashboard  = tab bar of 5 iframes:          │
                         │     /sup/         → sup-analysis              │
                         │     /verticals    → pact_verticals_analysis   │
                         │     /pi/          → production-incident-analysis│
                         │     /maintain/    → system-maintain-analysis  │
                         │     /game-status/ → game-status-analysis      │
                         └─────────────────────────────────────────────┘
                                   │                         │
                            gemini.py (Vertex AI)      Jira REST API v3
```

## The six sub-projects

| Folder | Role | Mount | Entry to read its CLAUDE.md when… |
|---|---|---|---|
| `service-desk-agent/` | **AI triage agent** + dashboard host. The single runnable app. | serves `:8080`, `/dashboard`, `/admin/*`, AI flows | touching AI flows, routing, mounts, the dashboard tab bar |
| `sup-analysis/` | SUP board analytics (3-phase pipeline + overall) | `/sup` | changing SUP metrics/reports |
| `pact_verticals_analysis/` | 8-board "Verticals" rollup (PACT/BUG/PF/MT/RNG/DEVOPS/DT/BO) | `/verticals` | changing verticals rollup |
| `production-incident-analysis/` | PI (Production Incident) board: severity, SLA, MTTR | `/pi` | changing PI dashboard |
| `system-maintain-analysis/` | Maintenance follow-list: sub-tasks of DEVOPS-511/486/405, Intake vs Resolved | `/maintain` | changing Recurring Issues board |
| `game-status-analysis/` | "Game Status" SVG flow graph across 5 spaces (ID/GAME/CER/LOC/RM); node = status w/ live count, click → ticket list | `/game-status` | changing Game Status flow/layout |

## The one mental model that covers all 4 dashboards

Every analytics board is the **same two/three-stage pipeline** — learn it once:

1. **Extract** — `script/<x>_extractor.py` hits the Jira API (`POST /rest/api/3/search/jql`,
   cursor pagination via `nextPageToken`) → writes a CSV in `result/`.
2. **Visualize** — `scratch/generate_<x>_html.py` reads that CSV, computes metrics,
   writes a **self-contained** HTML file in `result/` (Chart.js via CDN).
   Pure, testable logic lives in `scratch/report_logic.py` — never inlined.
3. **Serve** — `server.py` exports a Flask **Blueprint** with 4 routes:
   `GET /` (serves the HTML, `no-cache`), `POST /api/refresh` (incremental),
   `POST /api/refresh/full` (full), `GET /api/status`. `main.py` mounts each
   Blueprint at its URL prefix via `importlib`.

**Refresh buttons** (on every board): two floating buttons run the pipeline in a
background thread. The client JS derives its API prefix from
`window.location.pathname` (e.g. `startsWith('/maintain') ? '/maintain' : ''`) so the
same HTML works standalone (`/`) and inside the dashboard iframe (`/maintain/`).
It then polls `/api/status` until `running:false` and reloads. Cooldowns persist in
`localStorage` with a per-board key prefix (`sup_`, `pi_`, `maintain_`, …).

**Shared conventions across all analytics projects:**
- "Resolved/Done" statuses + an **effective resolved date** fallback chain
  (`Resolved Date` → `Status Category Change Date` → `Updated Date`).
- Working-hours math and ISO-week bucketing helpers in `report_logic.py`.
- `server.py` forces that project's own `.env` creds into the subprocess so the
  agent's Jira creds don't leak across tenants/projects.
- Incremental fetch via `SINCE_DATE` env → `AND updated >= "..."`, upsert by key.

So: to understand any board, read its `report_logic.py` (the metrics) and its
`generate_*_html.py` (the layout). The plumbing is identical to the others.

## service-desk-agent (the AI part) in one paragraph

`main.py` is the only entrypoint. Jira Automation posts webhooks; each endpoint
returns `202` immediately then does Gemini + Jira write-back on a background thread
(Jira Automation has a 5s timeout — **keep this async pattern**). Flows: `/triage`
(classify + route + auto-assign PIC + clone), `/scan` (PII/legal), `/rewrite`
(dev-task rewrite), `/summarise` (stale nudges), `/detect` (blocked linked issues).
Modes `on/test/off` gate Gemini/Jira-writes/chat (`MODE` env, default `test`).
All user text **must** pass `utils.sanitise()` and be wrapped in XML tags in prompts.
Full detail: `service-desk-agent/CLAUDE.md`.

## Configuration (one `.env` + per-component `config.toml`)

- **Root `.env`** (gitignored) — **all secrets**: Jira creds
  (`JIRA_DOMAIN`/`JIRA_EMAIL`/`JIRA_API_TOKEN`), `AGENT_KEY`, Google creds path,
  Google Chat + Jira Automation webhook URLs. Single source for every component.
- **`<component>/config.toml`** (committed) — that board/agent's **non-secret**
  behaviour: `project_key`, verticals `boards = [...]`, maintain `parents` +
  `[parent_labels]`, agent `mode`.
- **`config_loader.py`** (repo root) — every extractor / generator / `main.py` calls
  `config_loader.apply(__file__)` at startup. It loads the root `.env` and the caller's
  own `config.toml`, then maps values onto the env var names the code already reads
  (`JIRA_PROJECT_KEY`, `JIRA_PROJECT_{n}_KEY`, `MAINTAIN_PARENTS/PARENT_LABELS`, `MODE`,
  and derives `JIRA_BASE_URL`/`JIRA_USER_EMAIL` from the creds). Reads are unchanged;
  only the source moved. A new board ships a `config.toml` and calls `apply(__file__)` —
  no new `.env`.

## Run it

```bash
# Local (the whole thing):
cd service-desk-agent/scripts && python main.py    # :8080 → open /dashboard

# One board standalone (dev):
cd <board>-analysis && python server.py            # :5000

# Regenerate a board's data:
cd <board>-analysis
python script/<x>_extractor.py        # → result/<x>_tickets_export.csv
python scratch/generate_<x>_html.py   # → result/<x>_visual_report.html
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
- **`Dockerfile`** — `COPY . .` → install agent deps → `RUN bash build.sh` →
  `CMD python3 scripts/main.py`. It never needs editing when boards are added.
- **`.dockerignore`** — keeps `.venv/`, `venv/`, `__pycache__/`, `.git/`, `result/`
  out of the build context. **Must not** exclude `.env` — build-time extractors need
  each board's creds (carried in by `COPY . .`).
- **`docker-compose.yml`** — runs the `all-in-one` app (host networking) + an
  optional `cloudflared` tunnel (commented out by default).
- Each board reads creds from its own gitignored `.env`; the agent's creds are in
  `service-desk-agent/.env` (the compose `env_file`).

## Hard rules (apply everywhere)

- **Never commit** `.env` or `credentials.json` (gitignored per project). Never echo
  secrets into the repo.
- **Never delete or overwrite files in any `result/` directory** — they hold live
  generated data; regenerate via the pipeline instead of hand-editing.
- Jira: always `POST /rest/api/3/search/jql` (GET search is deprecated); paginate via
  `nextPageToken`; `timeout=30`; `time.sleep(0.5)` between pages.
- Do **not** add `Co-Authored-By` trailers to commits (repo convention).
- Keep pure logic in `report_logic.py`; keep the async-202 pattern in the agent.
