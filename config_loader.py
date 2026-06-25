"""
Shared configuration loader for the whole workspace.

Single source of truth:
  - root .env       — Jira credentials + all secrets (gitignored)
  - <component>/config.toml — that component's non-secret behaviour (committed)

Each component (board extractor/generator, or the agent) calls, at startup:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    import config_loader
    config_loader.apply(__file__)

`apply()` loads the root .env into os.environ and maps the caller's own
config.toml onto the env var names the existing code already reads, so downstream
`os.environ[...]` access is unchanged.
"""

import os
from pathlib import Path

try:
    import tomllib  # stdlib, Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - fallback for older runtimes
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"


def load_env() -> None:
    """Load the root .env into os.environ (setdefault — caller-injected vars win)."""
    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_PATH)
    except Exception:
        if ENV_PATH.exists():
            for line in ENV_PATH.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

    # Derive the agent's credential aliases from the shared Jira creds so both
    # naming conventions resolve from one place.
    domain = os.environ.get("JIRA_DOMAIN")
    email = os.environ.get("JIRA_EMAIL")
    if domain:
        os.environ.setdefault("JIRA_BASE_URL", f"https://{domain}")
    if email:
        os.environ.setdefault("JIRA_USER_EMAIL", email)


def load_board_config(caller_file: str) -> dict:
    """Read the caller component's own config.toml (next to its root dir)."""
    component_dir = Path(caller_file).resolve().parents[1]
    cfg_path = component_dir / "config.toml"
    if not cfg_path.exists():
        return {}
    with open(cfg_path, "rb") as f:
        return tomllib.load(f)


def _map_to_env(cfg: dict) -> None:
    """Map a component's config.toml onto the env var names existing code reads."""
    if "project_key" in cfg:
        os.environ.setdefault("JIRA_PROJECT_KEY", str(cfg["project_key"]))

    # Verticals: a list of board keys → JIRA_PROJECT_2_KEY … (matches
    # verticals_extractor.BOARD_ENV_KEYS, which starts at index 2).
    for i, key in enumerate(cfg.get("boards", []) or []):
        os.environ.setdefault(f"JIRA_PROJECT_{i + 2}_KEY", str(key))

    if "parents" in cfg:
        os.environ.setdefault("MAINTAIN_PARENTS", ",".join(cfg["parents"]))

    parent_labels = cfg.get("parent_labels") or {}
    if parent_labels:
        os.environ.setdefault(
            "MAINTAIN_PARENT_LABELS",
            ",".join(f"{k}={v}" for k, v in parent_labels.items()),
        )

    if "mode" in cfg:
        os.environ.setdefault("MODE", str(cfg["mode"]))


def apply(caller_file: str) -> dict:
    """Load root .env + the caller's config.toml into os.environ. Returns the config."""
    load_env()
    cfg = load_board_config(caller_file)
    _map_to_env(cfg)
    return cfg
