#!/usr/bin/env bash
# One-command build & deploy for the all-in-one dashboard stack.
#
#   ./deploy.sh              preflight → down → build → up -d
#   ./deploy.sh --no-cache   force a clean image rebuild
#   ./deploy.sh --logs       tail container logs after starting
set -euo pipefail
cd "$(dirname "$0")"

NO_CACHE=""
TAIL_LOGS=0
for arg in "$@"; do
  case "$arg" in
    --no-cache) NO_CACHE="--no-cache" ;;
    --logs)     TAIL_LOGS=1 ;;
    *) echo "Unknown flag: $arg (use --no-cache, --logs)" >&2; exit 2 ;;
  esac
done

# ── Compose command detection (v2 preferred, v1 fallback) ─────────────────────
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  echo "✗ Neither 'docker compose' nor 'docker-compose' is available." >&2
  exit 1
fi

# ── Preflight ─────────────────────────────────────────────────────────────────
echo "→ Preflight checks…"

if ! docker info >/dev/null 2>&1; then
  echo "✗ Docker daemon is not running. Start Docker and retry." >&2
  exit 1
fi

# Hard requirement: the single root .env (compose env_file + build-time creds).
if [ ! -f ".env" ]; then
  echo "✗ Missing root .env (required — Jira creds + secrets; copy .env.example)." >&2
  exit 1
fi

# Soft warning: Gemini credentials volume.
if [ ! -d "service-desk-agent/credentials" ]; then
  echo "⚠ service-desk-agent/credentials/ not found — Gemini/AI features will be"
  echo "  disabled, but the dashboards will still serve."
fi

# Soft warning: each board ships a committed config.toml (non-secret).
for comp in pact_verticals_analysis production-incident-analysis sup-analysis system-maintain-analysis service-desk-agent; do
  if [ ! -f "$comp/config.toml" ]; then
    echo "⚠ Missing $comp/config.toml — that component falls back to built-in defaults."
  fi
done

# ── Clean redeploy ────────────────────────────────────────────────────────────
echo "→ Stopping any existing stack…"
$COMPOSE down --remove-orphans || true

echo "→ Building image${NO_CACHE:+ (no cache)}…"
$COMPOSE build $NO_CACHE

echo "→ Starting stack…"
$COMPOSE up -d

# ── Report ────────────────────────────────────────────────────────────────────
echo ""
$COMPOSE ps
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "  Dashboard: http://localhost:8080/dashboard"
echo "  Logs:      $COMPOSE logs -f all-in-one"
echo "╚══════════════════════════════════════════════╝"

if [ "$TAIL_LOGS" -eq 1 ]; then
  echo "→ Tailing logs (Ctrl+C to stop)…"
  $COMPOSE logs -f all-in-one
fi
