"""
Game Status visualizer.

Reads result/game_status_tickets.csv, buckets tickets by (Space, Status) onto the
fixed flow graph in graph_layout.py, and writes a self-contained SVG flow diagram
(result/game_status_visual_report.html). Each status node shows its live ticket
count; clicking a node opens a right panel listing those tickets (Key + Summary +
Assignee + link to Jira). All ticket data is embedded at generation time, so the
panel works client-side with no live API call.
"""

import os
import sys
import json
import html
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------
# LOAD config (root .env + this board's config.toml)
# ---------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config_loader
config_loader.apply(__file__)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import graph_layout as G
from shared import timeline_modal
from overview_view import OVERVIEW_CSS, OVERVIEW_HTML, OVERVIEW_JS
from glossary_view import GLOSSARY_HTML
from control_center import CC_CSS, CC_HTML, CC_JS
import overview_logic

# Dynamically load status names from Jira statuses mapping file
STATUSES_PATH = Path(__file__).resolve().parents[1] / "result" / "jira_statuses.json"
if STATUSES_PATH.exists():
    try:
        _mapped_statuses = json.loads(STATUSES_PATH.read_text(encoding="utf-8"))
        for _nid, _node in G.NODES.items():
            _sid = _node.get("status_id")
            if _sid and _sid in _mapped_statuses:
                _node["status"] = _mapped_statuses[_sid]
                _node["label"] = _mapped_statuses[_sid]
    except Exception as _exc:
        print(f"WARNING: failed to load dynamic status names from {STATUSES_PATH}: {_exc}")

VERSION = "2026-06-16-v2"

BASE_DIR = Path(__file__).resolve().parents[1]
CSV_PATH = BASE_DIR / "result" / "game_status_tickets.csv"
LIMITS_PATH = BASE_DIR / "result" / "game_status_limits.json"
ACTUALS_PATH = BASE_DIR / "result" / "game_status_actuals.json"
LAST_SYNC_PATH = BASE_DIR / "result" / "game_status_last_sync.txt"
OUT_PATH = BASE_DIR / "result" / "game_status_visual_report.html"

# Config: parsed config.toml (for optional per-status [limits] overrides).
_CFG = config_loader.load_board_config(__file__)
LIMIT_OVERRIDES = _CFG.get("limits", {}) or {}

# WIP-limit display toggle. The limit-resolution pipeline (extractor fetch_limits,
# _load_limits/resolve_limit/capacity_class) is kept intact, but while the WIP limits
# aren't meaningful yet the flow nodes show only the ticket count — no "count/limit"
# pill text and no capacity colouring. Flip to True to re-enable the display.
SHOW_WIP_LIMIT = False

HALF_W = G.NODE_W / 2
HALF_H = G.NODE_H / 2

# Node/header icon styling (fixed indigo on a light tile — matches the design;
# capacity is conveyed by the pill + card border, not the icon).
ICON_COLOR = "#6366f1"
ICON_TILE = "#eef2ff"
HEADER_ICON_COLOR = "#4f46e5"

# Capacity palette: fg (text/icon), bg (pill), border (card).
CAP = {
    "green": {"fg": "#16a34a", "bg": "#dcfce7", "border": "#bbf7d0"},
    "orange": {"fg": "#ea580c", "bg": "#ffedd5", "border": "#fdba74"},
    "red":   {"fg": "#dc2626", "bg": "#fee2e2", "border": "#fca5a5"},
    "gray":  {"fg": "#64748b", "bg": "#f1f5f9", "border": "#e2e8f0"},
}


def _load_limits():
    """{project: {status: max}} from Jira board constraints (may be empty)."""
    if LIMITS_PATH.exists():
        try:
            return json.loads(LIMITS_PATH.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            print(f"WARNING: could not read {LIMITS_PATH}: {exc}")
    return {}


def resolve_limit(jira_limits, project, status):
    """Limit fallback chain: Jira board max → config override → no limit."""
    pmap = jira_limits.get(project, {})
    if status in pmap:
        return int(pmap[status])
    key = f"{project}:{status}"
    if key in LIMIT_OVERRIDES:
        return int(LIMIT_OVERRIDES[key])
    return 0


def capacity_class(current, limit):
    """Colour bucket per the design legend: <60% green, 60-90% orange, >90% red, 0 gray."""
    if current <= 0:
        return "gray"
    if not limit or limit <= 0:
        return "gray"
    pct = current / limit
    if pct < 0.6:
        return "green"
    if pct <= 0.9:
        return "orange"
    return "red"


# ---------------------------------------------------------
# DATA: count tickets + collect lists per node
# ---------------------------------------------------------
def build_node_data():
    """Return {node_id: {"count": int, "tickets": [..]}} keyed by graph node id."""
    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH).fillna("")
    else:
        print(f"WARNING: {CSV_PATH} not found — rendering empty graph.")
        df = pd.DataFrame(columns=["Ticket", "Space", "Status", "Summary", "Assignee", "URL"])

    jira_limits = _load_limits()
    node_data = {}
    for nid, node in G.NODES.items():
        if node.get("kind") == "start" or not node.get("status"):
            node_data[nid] = {"count": 0, "limit": 0, "tickets": []}
            continue
        mask = (df["Space"] == node["space"]) & (df["Status"] == node["status"])
        rows = df[mask]
        # Drop tickets already handed off (cloned forward to the next board).
        if "Cloned Forward" in rows.columns:
            rows = rows[rows["Cloned Forward"].fillna("").astype(str).str.strip() == ""]
        # For RELEASE board: only count tickets linked to at least one GAME ticket.
        if node["space"] == "RM" and "Has Game Child" in rows.columns:
            rows = rows[rows["Has Game Child"].fillna("").astype(str).str.strip() == "Yes"]
        tickets = [
            {
                "key": r["Ticket"],
                "summary": r["Summary"],
                "assignee": r.get("Assignee", "") or "Unassigned",
                "priority": r.get("Priority", "") or "",
                "game_type": r.get("Game Type", "") or "",
                "game_category": r.get("Game Category", "") or "",
                "wishful_date": r.get("Wishful Date", "") or "",
                "market": r.get("Market", "") or "",
                "batch": r.get("Batch", "") or "",
                "game_studio": r.get("Game Studio", "") or "",
                "status_category": r.get("Status Category", "") or "",
                "created": r.get("Created Date", "") or "",
                "updated": r.get("Updated Date", "") or "",
                "due_date": r.get("Due Date", "") or "",
                "rank": r.get("Rank", "") or "",
                "url": r["URL"],
            }
            for _, r in rows.iterrows()
        ]
        limit = resolve_limit(jira_limits, node["space"], node["status"])
        node_data[nid] = {"count": len(tickets), "limit": limit, "tickets": tickets}
    return node_data


# ---------------------------------------------------------
# SVG RENDERING
# ---------------------------------------------------------
def _esc(s):
    return html.escape(str(s), quote=True)


def _wrap(label, max_chars=16):
    words = str(label).split()
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines or [""]


def _icon(key, x, y, size=16, color="#475569"):
    """Render an ICONS glyph as a nested <svg> at (x, y) in canvas user space."""
    path = G.ICONS.get(key)
    if not path:
        return ""
    return (
        f'<svg x="{x:.0f}" y="{y:.0f}" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round">{path}</svg>'
    )


def _render_label(text, x, y):
    """Centered edge label with a white backing box for readability. May wrap on ' | '."""
    if not text:
        return ""
    lines = text.split(" | ")
    line_h = 14
    width = max(len(ln) for ln in lines) * 6.0 + 12
    height = len(lines) * line_h + 6
    top = y - height / 2
    tspans = ""
    for i, ln in enumerate(lines):
        ty = top + 14 + i * line_h
        weight = "700" if (":" in ln or i == 0) else "500"
        tspans += f'<text x="{x:.0f}" y="{ty:.0f}" text-anchor="middle" font-size="11" font-weight="{weight}" fill="#334155">{_esc(ln)}</text>'
    return (
        f'<rect x="{x - width/2:.0f}" y="{top:.0f}" width="{width:.0f}" height="{height:.0f}" '
        f'rx="4" fill="#ffffff" fill-opacity="0.92"/>{tspans}'
    )


def _edge_path_and_label(edge):
    src = G.NODES[edge["src"]]
    dst = G.NODES[edge["dst"]]
    route = edge.get("route", "down")

    if route == "wp":
        pts = edge["points"]
        lx, ly = edge.get("label_xy", (pts[len(pts) // 2][0], pts[len(pts) // 2][1]))
    elif route == "loop_left":
        ch = edge.get("channel", src["cx"] - HALF_W - 45)
        pts = [
            (src["cx"] - HALF_W, src["cy"]),
            (ch, src["cy"]),
            (ch, dst["cy"]),
            (dst["cx"] - HALF_W, dst["cy"]),
        ]
        lx, ly = edge.get("label_xy", (ch - 6, (src["cy"] + dst["cy"]) / 2))
    else:  # "down"
        sx, sy = src["cx"], src["cy"] + (G.START_R if src.get("kind") == "start" else HALF_H)
        if src.get("kind") == "start":
            tx, ty = src["cx"], _id_box_top()
        else:
            tx, ty = dst["cx"], dst["cy"] - HALF_H
        pts = [(sx, sy), (tx, ty)]
        lx, ly = edge.get("label_xy", (sx, (sy + ty) / 2))

    d = "M " + " L ".join(f"{px:.0f},{py:.0f}" for px, py in pts)
    path = f'<path d="{d}" fill="none" stroke="#94a3b8" stroke-width="1.6" marker-end="url(#arrow)"/>'
    return path + _render_label(edge.get("label", ""), lx, ly)


def _render_node(nid, node, data):
    cx, cy = node["cx"], node["cy"]
    if node.get("kind") == "start":
        # Icon (18px) + 5px gap + "Start" text (~28px) = ~51px total; centre the pair.
        icon_size = 18
        gap = 5
        text_w = 28  # approx pixel width of "Start" at font-size 14
        total = icon_size + gap + text_w
        ix = cx - total / 2          # icon left edge
        tx = ix + icon_size + gap + text_w / 2  # text anchor (middle)
        return (
            f'<g class="node-start">'
            f'<circle cx="{cx}" cy="{cy}" r="{G.START_R}" fill="#22c55e"/>'
            f'{_icon("play", ix, cy - icon_size / 2, size=icon_size, color="#ffffff")}'
            f'<text x="{tx:.1f}" y="{cy + 5:.1f}" text-anchor="middle" '
            f'font-size="14" font-weight="700" fill="#ffffff">Start</text>'
            f'</g>'
        )

    count = data["count"]
    limit = data.get("limit", 0)
    cls = capacity_class(count, limit) if SHOW_WIP_LIMIT else "gray"
    pal = CAP[cls]

    x = cx - HALF_W
    y = cy - HALF_H

    # Single row: icon tile (left) · label · capacity pill (right), all vertically centred.
    icon = (
        f'<rect x="{x + 9:.0f}" y="{cy - 12:.0f}" width="24" height="24" rx="7" fill="{ICON_TILE}"/>'
        f'{_icon(node.get("icon", ""), x + 13, cy - 8, size=16, color=ICON_COLOR)}'
    )

    pill_txt = f"{count}/{limit}" if (SHOW_WIP_LIMIT and limit) else str(count)
    pill_w = len(pill_txt) * 7.2 + 14
    pill_x = x + G.NODE_W - pill_w - 9
    pill = (
        f'<rect class="pill-rect" x="{pill_x:.0f}" y="{cy - 9:.0f}" width="{pill_w:.0f}" height="18" rx="9" fill="{pal["bg"]}"/>'
        f'<text class="pill-txt" x="{pill_x + pill_w/2:.0f}" y="{cy + 4:.0f}" text-anchor="middle" '
        f'font-size="11" font-weight="700" fill="{pal["fg"]}">{pill_txt}</text>'
    )

    # Label — left-aligned between the icon and the pill, wraps to at most 2 short lines.
    label_x = x + 41
    lines = _wrap(node["label"], max_chars=14)
    line_h = 12
    start_y = cy - (len(lines) - 1) * line_h / 2 + 4
    tspans = "".join(
        f'<text x="{label_x:.0f}" y="{start_y + i * line_h:.0f}" text-anchor="start" '
        f'font-size="11.5" font-weight="500" fill="#1e293b">{_esc(ln)}</text>'
        for i, ln in enumerate(lines)
    )

    # Card border tints for orange/red; neutral otherwise.
    bw = "2" if (SHOW_WIP_LIMIT and cls in ("orange", "red")) else "1.4"
    return (
        f'<g class="node" data-nid="{nid}" onclick="focusStatus(\'{nid}\')">'
        f'<rect class="card-rect" x="{x:.0f}" y="{y:.0f}" width="{G.NODE_W}" height="{G.NODE_H}" rx="9" '
        f'fill="#ffffff" stroke="{pal["border"]}" stroke-width="{bw}"/>'
        f'{icon}{tspans}{pill}'
        f'</g>'
    )


def _render_headers(space_totals):
    out = []
    for sp in G.SPACES:
        title = sp.get("title") or ""
        if title:
            hx, hy = sp["hx"], sp["hy"]
            # Centre the icon+title as one unit so the icon→title gap is always constant.
            icon_sz, gap = 24, 9
            total_text = f"{title} - {space_totals.get(sp['key'], 0)}"
            title_w = len(total_text) * 12.0  # approx width of 20px/800 uppercase
            has_icon = bool(sp.get("icon"))
            total_w = (icon_sz + gap if has_icon else 0) + title_w
            gx = hx - total_w / 2
            if has_icon:
                out.append(
                    f'<rect x="{gx:.0f}" y="{hy - 22:.0f}" width="{icon_sz}" height="{icon_sz}" rx="7" fill="{ICON_TILE}"/>'
                    f'{_icon(sp["icon"], gx + 4, hy - 18, size=16, color=HEADER_ICON_COLOR)}'
                )
            text_x = gx + (icon_sz + gap if has_icon else 0)
            out.append(
                f'<text x="{text_x:.0f}" y="{hy}" text-anchor="start" font-size="20" font-weight="800" fill="#0f172a" '
                f'data-space-total="{_esc(sp["key"])}">{_esc(total_text)}</text>'
            )
            if sp.get("subtitle"):
                out.append(
                    f'<text x="{hx}" y="{hy + 22}" text-anchor="middle" font-size="13" font-weight="600" fill="#94a3b8">{_esc(sp["subtitle"])}</text>'
                )
        if sp.get("subheader"):
            out.append(
                f'<text x="{sp["hx"]}" y="{sp.get("sub_y", sp["hy"] + 40)}" text-anchor="middle" '
                f'font-size="13" font-weight="700" letter-spacing="0.06em" fill="#2563eb">{_esc(sp["subheader"])}</text>'
            )
    return "\n".join(out)


def _space_box_nodes(key):
    sp = next(s for s in G.SPACES if s["key"] == key)
    return [n for n in G.NODES.values() if n["space"] == key
            and n.get("kind") != "start"
            and n.get("status") is not None
            and n["cx"] >= sp["hx"] - G.NODE_W]


def _id_box_top():
    """Top edge of the IDEAS space box (same formula as other boards)."""
    sp = next(s for s in G.SPACES if s["key"] == "ID")
    nodes = _space_box_nodes("ID")
    top_nodes = min(n["cy"] for n in nodes) - HALF_H
    header_top = sp["hy"] - 22
    return min(top_nodes - 24, header_top - 20)


def _render_space_boxes():
    """Faint rounded panel around each space's status nodes."""
    out = []
    for sp in G.SPACES:
        key = sp["key"]
        nodes = _space_box_nodes(key)
        if not nodes:
            continue
        left = min(n["cx"] for n in nodes) - HALF_W - 18
        right = max(n["cx"] for n in nodes) + HALF_W + 18
        top_nodes = min(n["cy"] for n in nodes) - HALF_H
        bottom = max(n["cy"] for n in nodes) + HALF_H + 32
        header_top = sp["hy"] - 22
        top = min(top_nodes - 24, header_top - 20)
        out.append(
            f'<rect x="{left:.0f}" y="{top:.0f}" width="{right - left:.0f}" height="{bottom - top:.0f}" '
            f'rx="16" fill="none" stroke="#64748b" stroke-opacity="0.2" stroke-width="1.5"/>'
        )
    return "\n".join(out)


def build_svg(node_data):
    space_totals = {
        sp["key"]: sum(
            data["count"]
            for nid, data in node_data.items()
            if G.NODES[nid].get("space") == sp["key"]
        )
        for sp in G.SPACES
    }
    boxes = _render_space_boxes()
    edges = "\n".join(_edge_path_and_label(e) for e in G.EDGES)
    nodes = "\n".join(_render_node(nid, node, node_data[nid]) for nid, node in G.NODES.items())
    marker = (
        '<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="9" refY="4.5" '
        'orient="auto" markerUnits="userSpaceOnUse">'
        '<path d="M0,0 L9,4.5 L0,9 Z" fill="#64748b"/></marker></defs>'
    )
    return (
        f'<svg id="flow" viewBox="0 0 {G.CANVAS_W} {G.CANVAS_H}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, system-ui, sans-serif">'
        f'{marker}{boxes}\n{edges}\n{_render_headers(space_totals)}\n{nodes}</svg>'
    )


# ---------------------------------------------------------
# HTML ASSEMBLY
# ---------------------------------------------------------
def _load_actuals():
    """{key: {stage: {entered, exited}}} from the changelog export (best-effort)."""
    if ACTUALS_PATH.exists():
        try:
            return json.loads(ACTUALS_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"WARNING: failed to read {ACTUALS_PATH}: {exc}")
    return {}


def _load_last_sync():
    """Last successful pipeline-run timestamp ("%Y-%m-%d %H:%M:%S"), or "" if never synced."""
    if LAST_SYNC_PATH.exists():
        try:
            return LAST_SYNC_PATH.read_text(encoding="utf-8").strip()
        except Exception as exc:
            print(f"WARNING: failed to read {LAST_SYNC_PATH}: {exc}")
    return ""


def build_overview():
    """Compute the overview dict from every GAME ticket + changelog actuals."""
    if not CSV_PATH.exists():
        overview = overview_logic.compute_overview([], {})
        overview["last_sync"] = _load_last_sync()
        return overview
    df = pd.read_csv(CSV_PATH).fillna("")
    games_df = df[df["Space"] == "GAME"]
    # Mirror the flow graph: drop GAME tickets already handed off (cloned forward).
    if "Cloned Forward" in games_df.columns:
        games_df = games_df[games_df["Cloned Forward"].astype(str).str.strip() == ""]
    games = [
        {
            "key": r["Ticket"],
            "summary": r.get("Summary", ""),
            "status": r.get("Status", ""),
            "created": r.get("Created Date", ""),
            "updated": r.get("Updated Date", ""),
            "due_date": r.get("Due Date", ""),
            "wishful_date": r.get("Wishful Date", ""),
            "game_studio": r.get("Game Studio", ""),
            "market": r.get("Market", ""),
            "game_category": r.get("Game Category", ""),
            "batch": r.get("Batch", ""),
        }
        for _, r in games_df.iterrows()
    ]
    overview = overview_logic.compute_overview(games, _load_actuals())
    overview["last_sync"] = _load_last_sync()
    return overview


def build_html(node_data):
    svg = build_svg(node_data)
    chartjs_path = Path(__file__).resolve().parent / "vendor" / "chart.umd.min.js"
    try:
        chartjs = chartjs_path.read_text(encoding="utf-8") if chartjs_path.exists() else ""
    except Exception as exc:
        print(f"WARNING: failed to read {chartjs_path}: {exc}")
        chartjs = ""
    as_of = _load_last_sync() or "latest export"

    def _space_label(key):
        sp = next((s for s in G.SPACES if s["key"] == key), None)
        if not sp:
            return key
        return sp.get("title") or sp.get("subheader") or key

    meta = {
        nid: {
            "title": node["label"],
            "space": _space_label(node["space"]),
            "space_key": node["space"],
            "count": node_data[nid]["count"],
            "limit": node_data[nid].get("limit", 0),
        }
        for nid, node in G.NODES.items()
        if node.get("kind") != "start"
    }
    tickets = {nid: node_data[nid]["tickets"] for nid in meta}
    spaces = [{"key": sp["key"], "label": _space_label(sp["key"])} for sp in G.SPACES]
    total = sum(node_data[nid]["count"] for nid in node_data)

    data_json = json.dumps(
        {"meta": meta, "tickets": tickets, "spaces": spaces}, ensure_ascii=False
    )
    overview_json = json.dumps(build_overview(), ensure_ascii=False)

    page = (
        _PAGE.replace("{{SVG}}", svg)
        .replace("{{DATA}}", data_json)
        .replace("{{OVERVIEW_DATA}}", overview_json)
        .replace("{{TOTAL}}", str(total))
        .replace("{{SHOW_WIP_LIMIT}}", "true" if SHOW_WIP_LIMIT else "false")
        .replace("{{OVERVIEW_CSS}}", OVERVIEW_CSS)
        .replace("{{OVERVIEW_HTML}}", OVERVIEW_HTML)
        .replace("{{OVERVIEW_JS}}", OVERVIEW_JS)
        .replace("{{GLOSSARY_HTML}}", GLOSSARY_HTML)
        .replace("{{CC_CSS}}", CC_CSS)
        .replace("{{CC_HTML}}", CC_HTML)
        .replace("{{CC_JS}}", CC_JS)
        .replace("{{CHARTJS}}", chartjs)
        .replace("{{AS_OF}}", as_of)
    )
    # Inject the shared timeline modal last (its braces must not hit other templating).
    return timeline_modal.render_into(page)


_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Game Status</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f1f5f9; color: #0f172a; }
  .canvas-wrap { padding: 20px; overflow: auto; }
  #flow { width: 100%; height: auto; min-width: 1480px; display: block; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; }
  .node rect { transition: stroke 0.12s, filter 0.12s; }
  .node { cursor: pointer; }
  .node:hover rect { stroke: #2563eb; stroke-width: 2.2; }

  /* ── Flow board: horizontal pipeline (light theme) ─────────────────────── */
  .pipeline { overflow-x: auto; padding: 4px 2px 10px; }
  .startbar { display: flex; align-items: flex-end; margin-bottom: 2px; }
  .startslot { flex: 1 1 0; min-width: 170px; display: flex; flex-direction: column; align-items: center; }
  .hspacer { flex: 0 0 40px; width: 40px; }
  .startnode { background: #16a34a; color: #fff; font-weight: 700; font-size: 12px; padding: 7px 16px; border-radius: 20px; box-shadow: 0 4px 12px rgba(22,163,74,.28); }
  .startline { width: 2px; height: 14px; background: #cbd5e1; }
  .gsflowrow { display: flex; gap: 0; align-items: stretch; position: relative; }
  .gsflowsvg { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; overflow: visible; z-index: 0; }
  .phase { flex: 1 1 0; min-width: 170px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; position: relative; z-index: 1; }
  .phhead { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 9px; border-bottom: 1px solid #e2e8f0; }
  .phname { font-weight: 700; font-size: 12.5px; letter-spacing: .3px; }
  .phtot { font-weight: 700; font-size: 15px; color: #334155; font-variant-numeric: tabular-nums; }
  .pstage { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 9px 11px; border: 1px solid #e2e8f0; background: #fff; border-radius: 9px; font-size: 12px; cursor: pointer; transition: .12s; color: #0f172a; }
  .pstage:hover { border-color: #6366f1; background: #eef2ff; }
  .pstage.zero { color: #94a3b8; }
  .pcount { font-weight: 700; background: #eef2ff; color: #4f46e5; border: 1px solid #e0e7ff; border-radius: 20px; min-width: 26px; text-align: center; padding: 1px 8px; font-size: 11px; font-variant-numeric: tabular-nums; }
  .pstage.zero .pcount { background: #f1f5f9; color: #94a3b8; border-color: #e2e8f0; }
  .hconn { flex: 0 0 40px; width: 40px; }
  .vconn { display: flex; flex-direction: column; align-items: center; padding: 1px 0; }
  .vconn .vline { width: 2px; height: 10px; background: #cbd5e1; }
  .vconn .vchev { width: 0; height: 0; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 7px solid #cbd5e1; }
  .declined { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: #64748b; background: #fff; border: 1px solid #e2e8f0; border-radius: 20px; padding: 5px 12px; margin-bottom: 12px; }
  .declined b { color: #dc2626; font-variant-numeric: tabular-nums; }

  .empty { padding: 28px 20px; color: #94a3b8; text-align: center; font-size: 0.9rem; }

  /* Tabbed table below the flow */
  .table-wrap { padding: 4px 24px 28px; }
  .table-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; }
  .tbl-header-row { display: flex; align-items: center; border-bottom: 1px solid #e2e8f0; }
  .inc-tabs { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; flex: 1; border-bottom: none;
              padding: 4px 12px 0; background: #f8fafc; }
  .inc-tab { background: transparent; border: none; border-bottom: 2px solid transparent; color: #64748b;
             padding: 10px 16px; font-size: 0.84rem; font-weight: 600; cursor: pointer; white-space: nowrap;
             transition: all .15s; font-family: inherit; }
  .inc-tab:hover { color: #0f172a; background: rgba(99,102,241,.08); }
  .inc-tab.active { color: #6366f1; border-bottom-color: #6366f1; }
  .inc-tab .tab-cnt { font-weight: 700; color: #94a3b8; margin-left: 4px; }
  .inc-tab.active .tab-cnt { color: #6366f1; }
  #sort-indicator { margin-left: auto; display: none; align-items: center; gap: 6px;
                    font-size: 0.75rem; color: #6366f1; font-weight: 600; white-space: nowrap;
                    background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 20px;
                    padding: 3px 10px 3px 8px; }
  #sort-indicator .si-dot { width: 8px; height: 8px; border-radius: 50%; background: #6366f1; flex-shrink: 0; }
  #sort-indicator .si-clear { margin-left: 4px; cursor: pointer; color: #6366f1; font-size: 0.8rem; opacity: 0.6; }
  #sort-indicator .si-clear:hover { opacity: 1; }
  .inc-panel { display: none; overflow-x: auto; }
  .inc-panel.active { display: block; }
  .row-hl td { background: #eef2ff !important; }
  .col-status { width: 150px; white-space: nowrap; }
  .col-status .st-badge { display: inline-block; padding: 2px 9px; border-radius: 12px; font-size: 0.72rem;
                          font-weight: 700; background: #eef2ff; color: #4f46e5; }
  .col-asg { width: 150px; }
  /* Ticket table */
  .ticket-tbl { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  .ticket-tbl thead tr { background: #f8fafc; border-bottom: 2px solid #e2e8f0; position: sticky; top: 0; z-index: 1; }
  .ticket-tbl th { padding: 9px 10px; text-align: left; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em;
                   color: #94a3b8; text-transform: uppercase; white-space: nowrap; }
  .ticket-tbl th.sortable { cursor: pointer; user-select: none; }
  .ticket-tbl th.sortable:hover { color: #64748b; background: #f1f5f9; }
  .th-wrap { display: inline-flex; align-items: center; gap: 6px; }
  .sort-arrow { font-size: 0.78rem; color: #cbd5e1; transition: color .12s ease; }
  .sort-arrow.active { color: #6366f1; }
  .ticket-tbl td { padding: 9px 10px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
  .ticket-tbl tr:hover td { background: #f8fafc; }
  .ticket-tbl .col-id    { width: 88px;  white-space: nowrap; }
  .ticket-tbl .col-sum   { min-width: 180px; }
  .ticket-tbl .col-cat   { width: 110px; }
  .ticket-tbl .col-pri   { width: 76px;  white-space: nowrap; }
  .ticket-tbl .col-std   { width: 110px; }
  .ticket-tbl .col-mkt   { width: 80px;  white-space: nowrap; }
  .ticket-tbl .col-bat   { width: 90px;  white-space: nowrap; }
  .ticket-tbl .col-stat  { width: 120px; white-space: nowrap; }
  .ticket-tbl .col-dur   { width: 68px;  white-space: nowrap; color: #64748b; text-align: right; }
  .ticket-tbl .col-date  { width: 96px;  white-space: nowrap; color: #64748b; }
  .ticket-tbl .col-updated { width: 140px; min-width: 140px; white-space: nowrap; color: #64748b; }
  .ticket-tbl .col-wish  { width: 90px;  white-space: nowrap; color: #64748b; }
  .ticket-tbl .col-due   { width: 90px;  white-space: nowrap; color: #64748b; }
  .ticket-tbl .col-delay { width: 68px;  white-space: nowrap; color: #64748b; text-align: right; }
  .tbl-key { font-weight: 700; color: #2563eb; text-decoration: none; font-size: 0.82rem; }
  .tbl-key:hover { text-decoration: underline; }
  .pri { display: inline-block; padding: 2px 7px; border-radius: 12px; font-size: 0.72rem; font-weight: 700; }
  .pri-highest { background: #fee2e2; color: #dc2626; }
  .pri-high    { background: #ffedd5; color: #ea580c; }
  .pri-medium  { background: #fef9c3; color: #a16207; }
  .pri-low     { background: #dbeafe; color: #1d4ed8; }
  .pri-lowest  { background: #f1f5f9; color: #64748b; }
  .pri-default { background: #f1f5f9; color: #64748b; }
  .stat { display: inline-block; padding: 2px 9px; border-radius: 12px; font-size: 0.72rem; font-weight: 700; }
  .stat-todo       { background: #f1f5f9; color: #475569; }
  .stat-inprogress { background: #dbeafe; color: #1d4ed8; }
  .stat-done        { background: #dcfce7; color: #15803d; }
  .stat-red         { background: #fee2e2; color: #dc2626; }
  .stat-default     { background: #eef2ff; color: #4f46e5; }

  /* Refresh */
  #refresh-overlay { display:none; position:fixed; inset:0; background:rgba(15,23,42,0.78); z-index:9999;
                     flex-direction:column; align-items:center; justify-content:center; gap:18px; }
  #refresh-spinner { width:52px; height:52px; border:4px solid #475569; border-top-color:#818cf8; border-radius:50%; animation:spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  #refresh-msg { color:#f8fafc; font-size:1.05rem; }
  #refresh-hint { color:#94a3b8; font-size:0.82rem; }
  #refresh-close { display:none; margin-top:6px; padding:8px 20px; background:#334155; color:#f8fafc; border:none; border-radius:50px; font-size:0.88rem; font-weight:600; cursor:pointer; }
  .rbtns { position:fixed; right:20px; bottom:20px; z-index:1000; display:flex; flex-direction:column; gap:10px; align-items:flex-end; }
  .rbtns button { display:flex; align-items:center; gap:8px; border-radius:999px; font-family:inherit; font-weight:600; cursor:pointer;
                  justify-content:center; width:48px; height:48px; transition:transform .12s ease, box-shadow .12s ease, opacity .12s ease; }
  .rbtns button:hover:not(:disabled) { transform:translateY(-1px); }
  .rbtns button:disabled { cursor:not-allowed; opacity:0.7; }
  #btn-full { background:#1e293b; color:#cbd5e1; border:1px solid #334155; font-size:1.05rem; box-shadow:0 8px 20px rgba(15,23,42,0.2); }
  #btn-quick { background:linear-gradient(135deg,#6366f1,#8b5cf6); color:#fff; border:none; font-size:1.1rem; box-shadow:0 8px 22px rgba(99,102,241,0.35); }

  /* Filter bar */
  .filter-bar { padding: 10px 24px; background: #ffffff; border-bottom: 1px solid #e2e8f0;
                display: flex; align-items: center; gap: 10px; flex-wrap: wrap; position: sticky; top: 0; z-index: 40; }
  .flt-label { font-size: 0.78rem; font-weight: 700; color: #64748b; letter-spacing: 0.04em; text-transform: uppercase; white-space: nowrap; }
  .flt-search { min-width: 250px; flex: 1 1 320px; max-width: 420px; }
  .flt-search input { width: 100%; padding: 8px 12px; border: 1px solid #dbe2ea; border-radius: 10px;
                      background: #f8fafc; color: #0f172a; font: inherit; font-size: 0.84rem; }
  .flt-search input::placeholder { color: #94a3b8; }
  .flt-search input:focus { outline: none; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.12); background: #ffffff; }
  .btn-clear { font-size: 0.8rem; font-weight: 600; color: #6366f1; background: none; border: none;
               cursor: pointer; padding: 4px 8px; border-radius: 6px; white-space: nowrap; }
  .btn-clear:hover { background: #eef2ff; }
  .flt-multi-wrap { position: relative; }
  .flt-multi-btn { font-size: 0.82rem; font-family: inherit; padding: 5px 28px 5px 10px; border: 1px solid #e2e8f0;
                   border-radius: 8px; background: #f8fafc; color: #0f172a; cursor: pointer; white-space: nowrap;
                   min-width: 130px; text-align: left; position: relative; }
  .flt-multi-btn .flt-arrow { position: absolute; right: 9px; top: 50%; transform: translateY(-50%); font-size: 0.65rem; color: #94a3b8; }
  .flt-multi-btn:focus { outline: none; border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,0.15); }
  .flt-multi-btn.active { border-color: #6366f1; background-color: #eef2ff; }
  .flt-multi-dropdown { display: none; position: absolute; top: calc(100% + 4px); left: 0; min-width: 180px;
                        background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
                        box-shadow: 0 4px 16px rgba(0,0,0,0.10); z-index: 200; padding: 6px 0; }
  .flt-multi-dropdown.open { display: block; }
  .flt-multi-dropdown label { display: flex; align-items: center; gap: 8px; padding: 6px 14px;
                              font-size: 0.82rem; color: #0f172a; cursor: pointer; user-select: none; }
  .flt-multi-dropdown label:hover { background: #f1f5f9; }
  .flt-multi-dropdown input[type=checkbox] { accent-color: #6366f1; width: 14px; height: 14px; cursor: pointer; }
  .flt-multi-divider { height: 1px; background: #e2e8f0; margin: 4px 0; }
  .flt-sep { width: 1px; height: 20px; background: #e2e8f0; flex-shrink: 0; }
  .flt-badge { font-size: 0.72rem; font-weight: 700; background: #6366f1; color: #fff;
               padding: 2px 8px; border-radius: 10px; white-space: nowrap; }
/*__TIMELINE_CSS__*/
{{OVERVIEW_CSS}}
{{CC_CSS}}
</style>
<script>{{CHARTJS}}</script>
</head>
<body>
<div id="vt-bar">
  <div id="vt-switch">
    <button class="vt-btn active" data-view="overview">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
      Overview
    </button>
    <button class="vt-btn" data-view="flow">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/><path d="M10 6h4a4 4 0 0 1 4 4v4"/></svg>
      Flow
    </button>
    <button class="vt-btn" data-view="glossary">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4h6a3 3 0 0 1 3 3v13a2.5 2.5 0 0 0-2.5-2.5H3z"/><path d="M21 4h-6a3 3 0 0 0-3 3v13a2.5 2.5 0 0 1 2.5-2.5H21z"/></svg>
      Glossary
    </button>
  </div>
  <div id="vt-spacer"></div>
  <div id="vt-asof"></div>
</div>

{{OVERVIEW_HTML}}

<div id="view-flow">
{{CC_HTML}}
</div>
<!-- /view-flow -->

{{GLOSSARY_HTML}}

<!-- Refresh -->
<div id="refresh-overlay">
  <div id="refresh-spinner"></div>
  <p id="refresh-msg">Pulling latest data from Jira…</p>
  <p id="refresh-hint">This takes ~10s–2min</p>
  <button id="refresh-close" onclick="dismissOverlay()">✕ Close</button>
</div>
<div class="rbtns">
  <button id="btn-full" onclick="doRefresh('full')" title="Full Refresh (~2 min)" aria-label="Full Refresh">🔄</button>
  <button id="btn-quick" onclick="doRefresh('quick')" title="Quick Refresh (~10s)" aria-label="Quick Refresh">⚡</button>
</div>

<!--__TIMELINE_HTML__-->

<script id="gs-data" type="application/json">{{DATA}}</script>
<script id="gs-overview" type="application/json">{{OVERVIEW_DATA}}</script>
<script>
  const DATA = JSON.parse(document.getElementById('gs-data').textContent);
  const SHOW_WIP_LIMIT = {{SHOW_WIP_LIMIT}};  // WIP-limit pill/colour display toggle (see generator).

  function esc(s){ const d=document.createElement('div'); d.textContent=(s==null?'':s); return d.innerHTML; }

/*__TIMELINE_JS__*/

{{CC_JS}}

{{OVERVIEW_JS}}
</script>
</body>
</html>"""


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    os.makedirs(BASE_DIR / "result", exist_ok=True)
    node_data = build_node_data()
    html_out = build_html(node_data)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)
    total = sum(d["count"] for d in node_data.values())
    print(f"Wrote {OUT_PATH} — {total} tickets across {len(G.NODES)} nodes / {len(G.SPACES)} spaces.")
