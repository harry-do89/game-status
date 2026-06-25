import sys
import logging
from pathlib import Path
from flask import Flask

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

from dotenv import load_dotenv
load_dotenv()

# Load root .env + this component's config.toml before importing the board.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config_loader
config_loader.apply(__file__)

app = Flask(__name__)

# ── Game Status dashboard (mounted at / — the dashboard IS the site) ───────────
try:
    import importlib.util as _ilu
    _gs_server_path = Path(__file__).resolve().parents[2] / "game-status-analysis" / "server.py"
    _spec = _ilu.spec_from_file_location("game_status_server", str(_gs_server_path))
    _gs_server = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_gs_server)
    app.register_blueprint(_gs_server.game_status_bp)
    logging.info("Game Status dashboard mounted at /")
except Exception as _e:
    logging.warning(f"Game Status dashboard not loaded: {_e}")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
