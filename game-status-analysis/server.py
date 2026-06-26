"""
Game Status board server.

Two usage modes:
  1. Standalone:  python server.py  (binds 0.0.0.0:5000)
  2. Blueprint:   from server import game_status_bp
                  app.register_blueprint(game_status_bp, url_prefix='/game-status')

The Blueprint exposes:
  GET  /                  → serves result/game_status_visual_report.html
  POST /api/refresh       → incremental re-fetch + re-render (background)
  POST /api/refresh/full  → full re-fetch + re-render (background)
  GET  /api/status        → {running, last_refresh, mode, error}
"""

import os
import threading
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

from flask import Flask, Blueprint, send_file, jsonify, Response

VERSION = "2026-06-16-v1"

BASE_DIR       = Path(__file__).resolve().parent
REPORT_PATH    = BASE_DIR / "result" / "game_status_visual_report.html"
CSV_PATH       = BASE_DIR / "result" / "game_status_tickets.csv"
LAST_SYNC_PATH = BASE_DIR / "result" / "game_status_last_sync.txt"

_venv_python = BASE_DIR / ".venv" / "bin" / "python"
PYTHON = str(_venv_python) if _venv_python.exists() else "/usr/bin/python3"

_state: dict = {"running": False, "last_refresh": None, "mode": None, "error": None}
_lock = threading.Lock()


def _csv_max_updated(csv_path) -> str:
    """Return max(Updated Date) in CSV minus 5 min as 'YYYY-MM-DD HH:MM'. None on error."""
    import csv as _csv_mod
    try:
        with open(csv_path, newline="") as f:
            dates = [
                row["Updated Date"] for row in _csv_mod.DictReader(f)
                if row.get("Updated Date", "").strip()
            ]
        if not dates:
            return None
        clean = max(dates).split(".")[0].replace("T", " ")
        for sep in ("+", "-"):
            if sep in clean[10:]:
                clean = clean[: clean.index(sep, 10)]
        max_dt = datetime.strptime(clean.strip(), "%Y-%m-%d %H:%M:%S")
        return (max_dt - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
    except Exception as exc:
        print(f"[game-status] _csv_max_updated error: {exc}")
        return None


def run_pipeline(mode: str = "full"):
    """Run game_status_extractor + generate_game_status_html in a background thread."""
    try:
        now_str = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[game-status] server.py {VERSION} — pipeline start [{mode}] at {now_str}", flush=True)
        env = {**os.environ}

        # Force the root .env creds into the subprocess (belt-and-suspenders;
        # the extractor/generator also self-load via config_loader).
        _env_file = BASE_DIR.parent / ".env"
        if _env_file.exists():
            for _line in _env_file.read_text().splitlines():
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    env[_k.strip()] = _v.strip()
            print(f"[game-status] loaded .env — JIRA_DOMAIN={env.get('JIRA_DOMAIN', '?')}", flush=True)
        else:
            print(f"[game-status] WARNING: {_env_file} not found — subprocess inherits parent Jira creds", flush=True)

        if mode == "incremental":
            since_str = None
            if LAST_SYNC_PATH.exists():
                try:
                    raw = LAST_SYNC_PATH.read_text().strip()
                    sync_dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
                    since_str = (sync_dt - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
                    print(f"[game-status] incremental — last_sync={raw} → SINCE_DATE={since_str}")
                except Exception as exc:
                    print(f"[game-status] last_sync parse error: {exc}, falling back to CSV max")
            if since_str is None and CSV_PATH.exists():
                since_str = _csv_max_updated(CSV_PATH)
                if since_str:
                    print(f"[game-status] incremental — CSV max fallback: SINCE_DATE={since_str}")
            if since_str:
                env["SINCE_DATE"] = since_str
            else:
                env.pop("SINCE_DATE", None)
                print(f"[game-status] incremental fallback to full (no sync anchor available)")
        else:
            env.pop("SINCE_DATE", None)
            print(f"[game-status] full re-fetch")

        scripts = [
            (BASE_DIR / "script" / "game_status_extractor.py",       300 if mode == "incremental" else 600),
            (BASE_DIR / "scratch" / "generate_game_status_html.py",  120),
        ]
        for script, timeout in scripts:
            try:
                result = subprocess.run(
                    [PYTHON, str(script)],
                    cwd=str(BASE_DIR),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                _state["error"] = f"{script.name} timed out after {timeout}s"
                return
            for line in (result.stdout + result.stderr).splitlines():
                if "NotOpenSSLWarning" not in line and "warnings.warn" not in line:
                    print(f"[game-status:{script.name}] {line}", flush=True)
            if result.returncode != 0:
                full_err = (result.stderr or result.stdout).strip()
                _state["error"] = full_err[-1000:]
                return

        _state["last_refresh"] = now_str
        LAST_SYNC_PATH.write_text(now_str)
        print(f"[game-status] pipeline done [{mode}] — data up to {now_str}", flush=True)

    except Exception as exc:
        _state["error"] = str(exc)
    finally:
        with _lock:
            _state["running"] = False


# ── Blueprint ─────────────────────────────────────────────────────────────────
game_status_bp = Blueprint("game_status", __name__)


@game_status_bp.route("/")
def game_status_index():
    if REPORT_PATH.exists():
        resp = send_file(REPORT_PATH)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"]        = "no-cache"
        resp.headers["Expires"]       = "0"
        return resp
    return Response(
        "<p>Report not found. Click Refresh or run "
        "<code>python scratch/generate_game_status_html.py</code> first.</p>",
        status=404,
        mimetype="text/html",
    )


@game_status_bp.route("/api/refresh", methods=["POST"])
def game_status_refresh():
    with _lock:
        if _state["running"]:
            return jsonify({"running": True, "message": "already running"})
        _state["running"] = True
        _state["mode"]    = "incremental"
        _state["error"]   = None
    threading.Thread(target=run_pipeline, args=("incremental",), daemon=True).start()
    return jsonify({"running": True, "message": "incremental refresh started"})


@game_status_bp.route("/api/refresh/full", methods=["POST"])
def game_status_refresh_full():
    with _lock:
        if _state["running"]:
            return jsonify({"running": True, "message": "already running"})
        _state["running"] = True
        _state["mode"]    = "full"
        _state["error"]   = None
    threading.Thread(target=run_pipeline, args=("full",), daemon=True).start()
    return jsonify({"running": True, "message": "full refresh started"})


@game_status_bp.route("/api/status")
def game_status_status():
    return jsonify(_state)


GAME_STAGES = [
    "Planned", "Math", "Contract Alignment", "Development",
    "Integration QC", "Optimization", "Packaging", "Done",
]
TIMELINE_VISIBLE_STAGES = [s for s in GAME_STAGES if s not in {"Planned", "Done"}]
SUBSTAGE_PATH = BASE_DIR / "result" / "game_status_substages.json"

TIMELINE_FIELD_NAMES = {
    "Math": {
        "eta": "ETA (Math)",
        "actual_start": "Actual Start (Math)",
        "actual_end": "Actual End (Math)",
    },
    "Contract Alignment": {
        "eta": "ETA (Contract Alignment)",
        "actual_start": "Actual Start (Contract Alignment)",
        "actual_end": "Actual End (Contract Alignment)",
    },
    "Development": {
        "eta": "ETA (Development)",
        "actual_start": "Actual Start (Development)",
        "actual_end": "Actual End (Development)",
    },
    "Integration QC": {
        "eta": "ETA (Integration QC)",
        "actual_start": "Actual Start (Integration QC)",
        "actual_end": "Actual End (Integration QC)",
    },
    "Optimization": {
        "eta": "ETA (Optimization)",
        "actual_start": "Actual Start (Optimization)",
        "actual_end": "Actual End (Optimization)",
    },
}

_timeline_field_ids_cache = None


def _jira_creds():
    """(domain, email, token) from os.environ, overlaid by the root .env if present."""
    env = {**os.environ}
    _env_file = BASE_DIR.parent / ".env"
    if _env_file.exists():
        for _line in _env_file.read_text().splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                env[_k.strip()] = _v.strip()
    return env.get("JIRA_DOMAIN", ""), env.get("JIRA_EMAIL", ""), env.get("JIRA_API_TOKEN", "")


def _stage_times(domain, email, token, key):
    """{stage: {entered, exited}} from a ticket's status changelog, for GAME_STAGES."""
    import requests as _req
    from requests.auth import HTTPBasicAuth as _Auth

    auth, headers, events, start_at = _Auth(email, token), {"Accept": "application/json"}, [], 0
    while True:
        url = f"https://{domain}/rest/api/3/issue/{key}/changelog"
        r = _req.get(url, auth=auth, headers=headers,
                     params={"startAt": start_at, "maxResults": 100}, timeout=15)
        if r.status_code != 200:
            print(f"[game-status] changelog {key}: HTTP {r.status_code}", flush=True)
            break
        data = r.json()
        for entry in data.get("values", []):
            ts = entry.get("created", "")
            for item in entry.get("items", []):
                if item.get("field") == "status":
                    events.append({"created": ts, "from": item.get("fromString", ""), "to": item.get("toString", "")})
        if data.get("isLast", True):
            break
        start_at += len(data.get("values", [])) or 100

    events.sort(key=lambda e: e["created"])
    out: dict = {}
    for ev in events:
        frm, to, ts = ev["from"], ev["to"], ev["created"]
        if to in GAME_STAGES:
            out.setdefault(to, {})["entered"] = ts
        if frm in GAME_STAGES and "exited" not in out.get(frm, {}):
            out.setdefault(frm, {})["exited"] = ts
    return out


def _ticket_created(key):
    """Created Date for a ticket from the CSV export, or '' if not found."""
    import csv as _csv_mod
    try:
        with open(CSV_PATH, newline="") as f:
            for row in _csv_mod.DictReader(f):
                if row.get("Ticket") == key:
                    return row.get("Created Date", "")
    except Exception:
        pass
    return ""


def _timeline_field_ids(domain, email, token):
    """Resolve Jira field display names to customfield ids for the timeline."""
    global _timeline_field_ids_cache
    if _timeline_field_ids_cache is not None:
        return _timeline_field_ids_cache

    import requests as _req
    from requests.auth import HTTPBasicAuth as _Auth

    wanted = {
        field_name
        for names in TIMELINE_FIELD_NAMES.values()
        for field_name in names.values()
    }
    auth = _Auth(email, token)
    headers = {"Accept": "application/json"}
    url = f"https://{domain}/rest/api/3/field"
    r = _req.get(url, auth=auth, headers=headers, timeout=15)
    r.raise_for_status()

    name_to_id = {}
    for field in r.json():
        name = (field.get("name") or "").strip()
        if name in wanted:
            name_to_id[name] = field.get("id")

    resolved = {}
    for stage, names in TIMELINE_FIELD_NAMES.items():
        resolved[stage] = {slot: name_to_id.get(field_name) for slot, field_name in names.items()}
    _timeline_field_ids_cache = resolved
    return resolved


def _ticket_timeline_fields(domain, email, token, key):
    """Return per-stage timeline dates from Jira custom fields on the issue itself."""
    import requests as _req
    from requests.auth import HTTPBasicAuth as _Auth

    field_ids = _timeline_field_ids(domain, email, token)
    wanted_ids = sorted({
        field_id
        for stage_fields in field_ids.values()
        for field_id in stage_fields.values()
        if field_id
    })
    if not wanted_ids:
        return {}

    auth = _Auth(email, token)
    headers = {"Accept": "application/json"}
    url = f"https://{domain}/rest/api/3/issue/{key}"
    r = _req.get(
        url,
        auth=auth,
        headers=headers,
        params={"fields": ",".join(wanted_ids)},
        timeout=15,
    )
    r.raise_for_status()
    issue_fields = (r.json() or {}).get("fields", {})

    out = {}
    for stage, stage_fields in field_ids.items():
        out[stage] = {
            slot: issue_fields.get(field_id) if field_id else None
            for slot, field_id in stage_fields.items()
        }
    return out


@game_status_bp.route("/api/ticket/<key>/changelog")
def ticket_changelog(key):
    """Return real stage-transition dates from Jira changelog for one ticket."""
    domain, email, token = _jira_creds()
    if not domain or not email or not token:
        return jsonify({"key": key, "transitions": [], "error": "Jira creds not configured"})
    try:
        st = _stage_times(domain, email, token, key)
        transitions = [
            {"stage": s, "entered": st[s].get("entered"), "exited": st[s].get("exited")}
            for s in GAME_STAGES if s in st
        ]
        return jsonify({"key": key, "transitions": transitions})
    except Exception as exc:
        print(f"[game-status] changelog error for {key}: {exc}", flush=True)
        return jsonify({"key": key, "transitions": [], "error": str(exc)})


@game_status_bp.route("/api/ticket/<key>/timeline")
def ticket_timeline(key):
    """Unified per-ticket timeline: 8 top GAME stages + nested Development sub-stages.

    Each entry: {name, level, actual_start, actual_end, eta}. Top stages read their
    values from Jira issue custom fields like "ETA (Math)" / "Actual Start (Math)" /
    "Actual End (Math)"; Development sub-stages still come from the extractor's
    per-parent cache file. The shared timeline modal (shared/timeline_modal.py)
    consumes this from any board.
    """
    import json as _json

    domain, email, token = _jira_creds()
    if not domain or not email or not token:
        return jsonify({"key": key, "stages": [], "estimated": True, "error": "Jira creds not configured"})

    try:
        # GAME and CER tickets share the same per-stage custom fields
        # (ETA/Actual Start/Actual End per stage), so both use the field-driven path.
        stage_fields = _ticket_timeline_fields(domain, email, token, key)

        # Development sub-stages from the extractor's per-parent file.
        subs = {}
        if SUBSTAGE_PATH.exists():
            subs = _json.loads(SUBSTAGE_PATH.read_text() or "{}")
        sub_rows = subs.get(key, [])

        stages = []
        for s in TIMELINE_VISIBLE_STAGES:
            t = stage_fields.get(s, {})
            stages.append({
                "name": s, "level": 0,
                "actual_start": t.get("actual_start"),
                "actual_end": t.get("actual_end"),
                "eta": t.get("eta"),
            })
            if s == "Development":
                for sr in sub_rows:
                    stages.append({
                        "name": sr.get("label", ""), "level": 1, "parent": "Development",
                        "actual_start": sr.get("entered"),
                        "actual_end": sr.get("exited"),
                        "eta": sr.get("eta"),
                    })

        has_top_level_data = any(
            any(v for v in (stage_fields.get(stage) or {}).values())
            for stage in TIMELINE_VISIBLE_STAGES
        )
        estimated = not has_top_level_data and not sub_rows
        return jsonify({"key": key, "stages": stages, "estimated": estimated})
    except Exception as exc:
        print(f"[game-status] timeline error for {key}: {exc}", flush=True)
        return jsonify({"key": key, "stages": [], "estimated": True, "error": str(exc)})


# ── Standalone mode ───────────────────────────────────────────────────────────
app = Flask(__name__)
app.register_blueprint(game_status_bp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[game-status] server.py {VERSION} — standalone http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
