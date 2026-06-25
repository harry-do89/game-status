#!/usr/bin/env bash
# Build all dashboards inside the Docker image: install each board's deps and
# pre-render its data (extractor → CSV → generator → HTML).
#
# ➕ To add a board: append ONE build_board line at the bottom.
#    The Dockerfile never changes — it just runs `bash build.sh`.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

build_board() {            # build_board <dir> <extractor> <generator>
  local dir="$1" extractor="$2" generator="$3"
  echo "=== building board: $dir ==="
  pip install -r "$ROOT/$dir/requirements.txt"
  ( cd "$ROOT/$dir" && python "$extractor" && python "$generator" )
}

build_board pact_verticals_analysis     script/verticals_extractor.py  scratch/generate_verticals_html.py
build_board production-incident-analysis script/pi_extractor.py         scratch/generate_pi_html.py
build_board sup-analysis                 script/sup_extractor_v2.py     scratch/generate_overall_html.py
build_board system-maintain-analysis     script/maintain_extractor.py   scratch/generate_maintain_html.py
build_board game-status-analysis         script/game_status_extractor.py scratch/generate_game_status_html.py
build_board board-priority-queue          script/priority_extractor.py    scratch/generate_priority_html.py
