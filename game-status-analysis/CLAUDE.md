# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git Commits

Do NOT add `Co-Authored-By` trailers to commits.

## Project Purpose

**Game Status** ("GAME PRODUCTION WORKFLOW") — a flow-diagram board that mirrors the
game-production workflow on `vvortech.atlassian.net`. Unlike the other dashboards
(chart pipelines), this board renders an **SVG flow graph**: five Jira projects
("spaces") as columns, each status a node showing a **capacity badge `current / limit`**
coloured by usage (🟢 <60% · 🟠 60–90% · 🔴 >90% · ⚪ 0). Each node has an icon; columns
have icon headers; a bottom Legend/Notes/Capacity panel explains the colours. Clicking a
node opens a right panel listing those tickets (Key + Summary + Assignee + link to Jira).

**WIP limit resolution (per node):** Jira board column `max` (from
`result/game_status_limits.json`) → `config.toml` `[limits]` override (`"PROJECT:Status"`)
→ `default_limit` (10). Colour bucket via `capacity_class()` in the generator.

### Spaces → Jira project → diagram statuses

| Column | Project | Statuses shown |
|---|---|---|
| IDEAS | `ID` | Pending Review, Declined, Approved for Production, Prioritized, Game Design & Math, Game Review & Art, Ready for Production with Game Mechanic (+ synthetic Start) |
| GAMES | `GAME` | Planned, Math, Contract Alignment, Development, Integration QC, Optimization, Packaging, Done |
| CERTIFICATION | `CER` | To Do, In Progress, Done |
| LOCALIZATION | `LOC` | To Do, In Progress, Done |
| RELEASE | `RM` | Requested, To Do, Production Ready, Monitoring, Released |

Only the statuses drawn in the diagram are counted; tickets in any other status
(e.g. RM `Backlog`/`UAT`) are excluded. Node **display labels** are decoupled from
the exact Jira **status** string used for count lookup (see `graph_layout.py`).
`ID`/`CER`/`LOC` may legitimately show 0 — those projects are new (LOCALIZATION is
flagged "wip").

## Serve & Share

Mounted as a Blueprint inside `../service-desk-agent/scripts/main.py` at
`/game-status`. The dashboard at `/dashboard` has a "🎮 Game Status" tab.

Standalone (dev): `python server.py` (binds 0.0.0.0:5000; honours `PORT`).

Refresh buttons work both standalone and inside the dashboard iframe:
- **⚡ Quick Refresh** — incremental (tickets updated since last sync), 60s cooldown
- **🔄 Full Refresh** — re-fetches all tickets, confirm dialog, 180s cooldown

Cooldowns persist in `localStorage` (keys prefixed `gamestatus_`). The client derives
the mount prefix from `window.location.pathname` so the same HTML works at `/` and
`/game-status/`. Endpoints: `POST /api/refresh`, `POST /api/refresh/full`, `GET /api/status`.

## Setup

Credentials come from the **root `.env`** (`JIRA_DOMAIN`/`JIRA_EMAIL`/`JIRA_API_TOKEN`).
This board's non-secret settings live in `config.toml` (committed):

```toml
spaces = ["ID", "GAME", "CER", "LOC", "RM"]
```

Both scripts call `config_loader.apply(__file__)` (repo-root `config_loader.py`); the
extractor reads `cfg["spaces"]` directly.

## Commands

```bash
# 1. Extract — hits Jira API, writes result/game_status_tickets.csv
python script/game_status_extractor.py

# 2. Visualize — reads CSV + graph_layout, writes result/game_status_visual_report.html
python scratch/generate_game_status_html.py
```

## Architecture

**Two-stage pipeline:**

1. **Extract** — `script/game_status_extractor.py` loops the 5 projects via
   `POST /rest/api/3/search/jql` (cursor pagination), writes `result/game_status_tickets.csv`.
   It also calls `JiraClient.fetch_limits()` (agile API: `board?projectKeyOrId=…` →
   `board/{id}/configuration`) and writes `result/game_status_limits.json` =
   `{project: {status: max}}` for columns that set a `max` (best-effort; never blocks the export).
2. **Visualize** — `scratch/generate_game_status_html.py` reads the CSV + limits JSON,
   buckets tickets by (Space, Status) onto the fixed graph, resolves each node's WIP limit,
   and renders a self-contained SVG flow diagram. All ticket data is embedded at generation
   time → the right panel works client-side with no live API call.

**Flow definition:** `scratch/graph_layout.py` — pure data (the presentation analogue
of the other boards' `report_logic.py`): `SPACES` (incl. `icon`/`subheader`/`subtitle`),
`NODES` (id → space/label/status/x/y/`icon`), `EDGES` (src/dst/label/route), and `ICONS`
(icon key → inline SVG path). **This is the single place to edit if the workflow changes.**
Edge `route` ∈ {`down`, `loop_left`, `wp` (explicit `points`)}; role labels are blank by
design — only `Reskin` / `Certification Needed` / `Localization needed` carry text.

**Server Blueprint:** `server.py` exports `game_status_bp`. Mounted at `/game-status`
by `../service-desk-agent/scripts/main.py` via `importlib`. Incremental anchor stored
in `result/game_status_last_sync.txt`. Forces this project's `.env` creds into the
subprocess.

## Timeline API

This board also exposes a per-ticket timeline route:

- `GET /api/ticket/<key>/timeline`

It powers the shared modal injected from `../shared/timeline_modal.py`.

### Source of truth for timeline rows

Top-level GAME timeline rows are **field-driven**, not changelog-driven.

- The server resolves Jira field display names to `customfield_xxx` ids at runtime
  through `GET /rest/api/3/field`.
- It then fetches the GAME issue itself and reads these fields per stage:
  - `ETA (Math)`, `Actual Start (Math)`, `Actual End (Math)`
  - `ETA (Contract Alignment)`, `Actual Start (Contract Alignment)`, `Actual End (Contract Alignment)`
  - `ETA (Development)`, `Actual Start (Development)`, `Actual End (Development)`
  - `ETA (Integration QC)`, `Actual Start (Integration QC)`, `Actual End (Integration QC)`
  - `ETA (Optimization)`, `Actual Start (Optimization)`, `Actual End (Optimization)`
- `Packaging` remains a visible stage in the response/UI, but there is no field mapping
  for it yet. Until new Jira fields are added, its `eta` / `actual_start` /
  `actual_end` will be `null`.
- `Planned` and `Done` are intentionally omitted from the timeline response and modal.

### Development sub-stages

Indented Development children (`BE`/`BO`/`Platform`/`FE`/`Math`) still come from
the extractor cache file `result/game_status_substages.json`.

- `script/game_status_extractor.py` labels sub-tasks from their summaries, fetches
  each child issue + changelog, and writes `{label, entered, exited, eta}` rows per
  GAME parent.
- The timeline route merges those cached rows under the top-level `Development` row.

### Important implementation note

Do not revert the timeline route back to top-level changelog parsing unless the data
contract changes. Changelog is still used elsewhere in this project, but the timeline
modal's main stage dates now come from explicit Jira fields on the GAME issue.

## CSV Schema (pipeline glue)

`result/game_status_tickets.csv`:

| Column | Notes |
|---|---|
| `Ticket` | Jira key (e.g. `GAME-194`) |
| `Space` | Project key (`ID`/`GAME`/`CER`/`LOC`/`RM`) |
| `Status` | Current Jira status (matched against node `status`) |
| `Status Category` | `statusCategory.name` |
| `Summary` | Ticket title |
| `Assignee` | `assignee.displayName`, "Unassigned" if null |
| `Created Date` / `Updated Date` | Timestamps |
| `URL` | `{JIRA_BASE_URL}/browse/{key}` (right-panel link) |

## Jira API Rules

- **Always** `POST /rest/api/3/search/jql`; cursor pagination via `nextPageToken`;
  `timeout=30`; `time.sleep(0.5)` between pages.
- **Incremental fetch:** `SINCE_DATE` env → JQL `AND updated >= "..."`; upsert by `Ticket`.
