# Game Status Engineering Suite

A single Jira-tenant (`vvortech.atlassian.net`) analytics suite: one read-only
**Game Status** dashboard, served by a thin Flask shell on port **8081**.

Open `http://localhost:8081/dashboard` — redirects to `/game-status/`.

> Architecture & per-project detail: see [`CLAUDE.md`](CLAUDE.md) and each
> sub-project's own `CLAUDE.md`.

## Prerequisites

- Docker + Docker Compose v2 (`docker compose version`)
- Credentials & config:
  - **`.env`** at the repo root — **required**, gitignored. Holds Jira creds
    (`JIRA_DOMAIN`/`JIRA_EMAIL`/`JIRA_API_TOKEN`). Copy `.env.example` → `.env`
    and fill in.
  - **`game-status-analysis/config.toml`** — committed, non-secret per-board
    settings (project key, etc). Edit in place.

## Deploy on Docker (one command)

```bash
./deploy.sh
```

This runs preflight checks, stops any running stack, builds the image (installing
the board's deps and pre-rendering its data via `build.sh`), and starts the
container detached. When it finishes:

```
Dashboard: http://localhost:8081/dashboard
Logs:      docker compose logs -f game-status
```

Flags:

| Command | Effect |
|---|---|
| `./deploy.sh` | preflight → `down` → `build` → `up -d` |
| `./deploy.sh --no-cache` | force a clean image rebuild |
| `./deploy.sh --logs` | tail container logs after starting |

### What's in `docker-compose.yml`

```yaml
services:
  game-status:
    build: .
    container_name: game-status
    env_file:
      - "./.env"
    network_mode: host
    restart: always
```

One service, built from the repo's `Dockerfile`, using `network_mode: host` —
the container binds directly to the host's network, so port `8081` is reachable
at `http://localhost:8081/dashboard` with no `ports:` mapping needed.

> **macOS note:** Docker Desktop on Mac does **not** expose `network_mode: host`
> to the host machine — `localhost:8081` will refuse to connect even though the
> container is healthy. This setup targets a **Linux host** (e.g. a VPS). If
> you're deploying/testing on a Mac, switch to bridge networking instead:
> ```yaml
>     ports:
>       - "8081:8081"
>     # remove the network_mode: host line
> ```

### Manual Docker commands (without `deploy.sh`)

```bash
docker compose build                   # build the image (runs build.sh — installs deps, pre-renders data)
docker compose up -d                   # start detached
docker compose logs -f game-status     # tail logs
docker compose down                    # stop and remove the container
```

### Exposing it publicly

`docker-compose.yml` only runs the dashboard container itself. To expose it to
the internet, run your own tunnel/reverse proxy (e.g. a Cloudflare Tunnel)
pointing at `http://localhost:8081` on the same host.

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
2. Mount its Blueprint in `service-desk-agent/scripts/main.py` (copy the existing
   `/game-status` block).
3. Append **one line** to [`build.sh`](build.sh):
   ```bash
   build_board <board-dir> script/<x>_extractor.py scratch/generate_<x>_html.py
   ```
4. `./deploy.sh` — done. The build log shows `=== building board: <board-dir> ===`.

## Local development (no Docker)

```bash
# The whole app:
cd service-desk-agent/scripts && python main.py     # :8081 → /dashboard

# Game Status standalone:
cd game-status-analysis && python server.py        # :5000

# Regenerate the board's data:
cd game-status-analysis
python script/game_status_extractor.py        # → result/game_status_tickets_export.csv
python scratch/generate_game_status_html.py    # → result/game_status_visual_report.html
```

