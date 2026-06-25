"""
Game Status flow definition (pure data — the presentation analogue of report_logic.py).

This is the single place that describes the *fixed* game-production workflow drawn
in the design mock: the 5 spaces (columns), every status node with its SVG position
and icon, and every arrow (edge). Ticket *counts* and *WIP limits* are dynamic
(filled by the generator from the CSV + Jira board limits); the graph *shape* lives
here. Edit this file if the Jira workflow changes.

Coordinate system: an SVG canvas of CANVAS_W x CANVAS_H. Each node is positioned by
its CENTER (cx, cy). Node display labels are decoupled from the exact Jira `status`
string used to look up counts (e.g. node "Approve for Production" → status
"Approved for Production").

Per the "GAME PRODUCTION WORKFLOW" redesign: per-arrow role labels are dropped
(only `Reskin` and the cross-space `Certification Needed` / `Localization needed`
remain), and each node / column carries an `icon` key resolved against ICONS.
"""

CANVAS_W = 2100
CANVAS_H = 1570

NODE_W = 285
NODE_H = 64
START_R = 38

# ── Spaces (columns) — order = left-to-right ────────────────────────────────────
# IDEAS has no big title: it shows the Start pill + an "INTAKE & PRIORITIZATION"
# sub-header (matching the design). Other columns carry an icon + title (+subtitle).
# Uniform vertical rhythm: every status row is PITCH apart, first row at ROW0.
ROW0 = 305
PITCH = 150


def _row(i):
    return ROW0 + i * PITCH


SPACES = [
    {"key": "ID",   "title": "IDEAS",         "hx": 510,  "hy": 205, "icon": "lightbulb"},
    {"key": "GAME", "title": "GAMES",         "hx": 890,  "hy": 205, "icon": "gamepad"},
    {"key": "CER",  "title": "CERTIFICATION", "hx": 1320, "hy": 205, "icon": "shield"},
    {"key": "LOC",  "title": "LOCALIZATION",  "hx": 1320, "hy": 812, "icon": "globe"},
    {"key": "RM",   "title": "RELEASE",       "hx": 1750, "hy": 205, "icon": "rocket"},
]

# ── Forward hand-off mapping (which board(s) a ticket is cloned into next) ───────
# A ticket that has a Jira "Cloners" link to a ticket in one of its NEXT_SPACES has
# been handed off and is no longer counted on its current board.
NEXT_SPACES = {
    "ID":   ("GAME",),
    "GAME": ("CER", "LOC", "RM"),
    "CER":  ("RM",),
    "LOC":  ("RM",),
    "RM":   (),
}

# ── Nodes ───────────────────────────────────────────────────────────────────────
# space = Jira project key; status = exact Jira status (None for the synthetic Start).
NODES = {
    # IDEAS (project ID)
    "start":          {"space": "ID",   "label": "Start",                  "status": None,                                  "cx": 510,  "cy": 33, "kind": "start", "icon": "play"},
    "pending_review": {"space": "ID",   "label": "Pending Review",         "status": "Pending Review",                      "status_id": "12146", "cx": 510,  "cy": _row(0), "icon": "search"},
    "declined":       {"space": "ID",   "label": "Declined",               "status": "Declined",                            "status_id": "12060", "cx": 185,  "cy": _row(0), "icon": "x-circle"},
    "approved":       {"space": "ID",   "label": "Approve for Production",  "status": "Approved for Production",             "status_id": "12110", "cx": 510,  "cy": _row(1), "icon": "check-circle"},
    "prioritized":    {"space": "ID",   "label": "Prioritized",            "status": "Prioritized",                         "status_id": "12405", "cx": 510,  "cy": _row(2), "icon": "list"},
    "design_math":    {"space": "ID",   "label": "Game Design & Math",     "status": "Game Design & Math",                  "status_id": "12414", "cx": 510,  "cy": _row(3), "icon": "sliders"},
    "review_art":     {"space": "ID",   "label": "Game Review & Art",      "status": "Game Review & Art",                   "status_id": "12415", "cx": 510,  "cy": _row(4), "icon": "eye"},
    "ready_prod":     {"space": "ID",   "label": "Ready for Production",    "status": "Ready for Development",               "status_id": "12149", "cx": 510,  "cy": _row(5), "icon": "rocket"},

    # GAMES (project GAME)
    "planned":        {"space": "GAME", "label": "Planned",          "status": "Planned",           "status_id": "12150", "cx": 890, "cy": _row(0), "icon": "calendar"},
    "math":           {"space": "GAME", "label": "Math",             "status": "Math",              "status_id": "12393", "cx": 890, "cy": _row(1), "icon": "hash"},
    "contract":       {"space": "GAME", "label": "Contract Alignment","status": "Contract Alignment","status_id": "12412", "cx": 890, "cy": _row(2), "icon": "doc"},
    "development":    {"space": "GAME", "label": "Development",       "status": "Development",       "status_id": "3",     "cx": 890, "cy": _row(3), "icon": "code"},
    "integration_qc": {"space": "GAME", "label": "Integration QC",   "status": "Integration QC",    "status_id": "12397", "cx": 890, "cy": _row(4), "icon": "users"},
    "optimization":   {"space": "GAME", "label": "Optimization",     "status": "Optimization",      "status_id": "12417", "cx": 890, "cy": _row(5), "icon": "sliders"},
    "packaging":      {"space": "GAME", "label": "Packaging",        "status": "Packaging",         "status_id": "12048", "cx": 890, "cy": _row(6), "icon": "box"},
    "games_done":     {"space": "GAME", "label": "Done",             "status": "Ready to Release",  "status_id": "12457", "cx": 890, "cy": _row(7), "icon": "check"},

    # CERTIFICATION (project CER)
    "cert_todo":       {"space": "CER", "label": "To Do",       "status": "To Do",       "status_id": "10532", "cx": 1320, "cy": _row(0), "icon": "clipboard"},
    "cert_inprogress": {"space": "CER", "label": "In Progress", "status": "In Progress", "status_id": "12057", "cx": 1320, "cy": _row(1), "icon": "loader"},
    "cert_done":       {"space": "CER", "label": "Done",        "status": "Done",        "status_id": "10533", "cx": 1320, "cy": _row(2), "icon": "check"},

    # LOCALIZATION (project LOC) — starts at row 4 so it sits clearly below CERTIFICATION.
    "loc_todo":       {"space": "LOC", "label": "To Do",       "status": "To Do",       "status_id": "10532", "cx": 1320, "cy": _row(4), "icon": "translate"},
    "loc_inprogress": {"space": "LOC", "label": "In Progress", "status": "In Progress", "status_id": "12057", "cx": 1320, "cy": _row(5), "icon": "edit"},
    "loc_done":       {"space": "LOC", "label": "Done",        "status": "Done",        "status_id": "10533", "cx": 1320, "cy": _row(6), "icon": "check"},

    # RELEASE (project RM)
    "rel_requested":   {"space": "RM", "label": "Requested",        "status": "Requested",        "status_id": "12351", "cx": 1750, "cy": _row(0), "icon": "inbox"},
    "rel_todo":        {"space": "RM", "label": "To Do",            "status": "To Do",            "status_id": "10532", "cx": 1750, "cy": _row(1), "icon": "list"},
    "rel_prod_ready":  {"space": "RM", "label": "Production Ready",  "status": "Production Ready",  "status_id": "12352", "cx": 1750, "cy": _row(2), "icon": "cloud"},
    "rel_monitoring":  {"space": "RM", "label": "Monitoring",       "status": "Monitoring",       "status_id": "12353", "cx": 1750, "cy": _row(3), "icon": "loader"},
    "rel_released":    {"space": "RM", "label": "Released",         "status": "Released",         "status_id": "12050", "cx": 1750, "cy": _row(4), "icon": "send"},
}

# ── Edges ───────────────────────────────────────────────────────────────────────
# route:
#   "down"      straight vertical, src.bottom → dst.top (same column, forward)
#   "loop_left" backward within a column via a left-hand channel
#   "wp"        explicit polyline through absolute `points`; label placed at `label_xy`
# Role labels are intentionally blank per the redesign; only Reskin + the cross-space
# hand-offs keep a label.
EDGES = [
    # IDEAS
    {"src": "start",          "dst": "pending_review", "route": "down", "label": ""},
    {"src": "pending_review", "dst": "declined",       "route": "wp",   "label": "",
     "points": [(368, _row(0)), (327, _row(0))]},
    {"src": "pending_review", "dst": "approved",       "route": "down", "label": ""},
    {"src": "approved",       "dst": "prioritized",    "route": "down", "label": ""},
    {"src": "prioritized",    "dst": "design_math",    "route": "down", "label": ""},
    {"src": "design_math",    "dst": "review_art",     "route": "down", "label": ""},
    {"src": "review_art",     "dst": "ready_prod",     "route": "down", "label": ""},
    {"src": "ready_prod",     "dst": "planned",        "route": "wp",   "label": "",
     "points": [(368, _row(5)), (700, _row(5)), (700, _row(0)), (748, _row(0))]},

    # GAMES
    {"src": "planned",        "dst": "math",          "route": "down", "label": ""},
    {"src": "math",           "dst": "contract",      "route": "down", "label": ""},
    {"src": "contract",       "dst": "development",   "route": "down", "label": ""},
    {"src": "development",    "dst": "integration_qc","route": "down", "label": ""},
    {"src": "integration_qc", "dst": "optimization",  "route": "down", "label": ""},
    {"src": "optimization",   "dst": "packaging",     "route": "down", "label": ""},
    {"src": "packaging",      "dst": "games_done",    "route": "down", "label": ""},

    # CERTIFICATION
    {"src": "cert_todo",       "dst": "cert_inprogress", "route": "down", "label": ""},
    {"src": "cert_inprogress", "dst": "cert_done",       "route": "down", "label": ""},

    # LOCALIZATION
    {"src": "loc_todo",       "dst": "loc_inprogress", "route": "down", "label": ""},
    {"src": "loc_inprogress", "dst": "loc_done",       "route": "down", "label": ""},

    # RELEASE
    {"src": "rel_requested",  "dst": "rel_todo",        "route": "down", "label": ""},
    {"src": "rel_todo",       "dst": "rel_prod_ready",  "route": "down", "label": ""},
    {"src": "rel_prod_ready", "dst": "rel_monitoring",  "route": "down", "label": ""},
    {"src": "rel_monitoring", "dst": "rel_released",    "route": "down", "label": ""},

    # Cross-space (automated / hand-off moves)
    {"src": "games_done", "dst": "cert_todo", "route": "wp", "label": "",
     "points": [(1032, _row(7)), (1105, _row(7)), (1105, _row(0)), (1178, _row(0))], "label_xy": (1116, _row(1))},
    {"src": "games_done", "dst": "loc_todo", "route": "wp", "label": "",
     "points": [(1032, _row(7)), (1130, _row(7)), (1130, _row(4)), (1178, _row(4))], "label_xy": (1141, _row(6))},
    {"src": "cert_done",  "dst": "rel_requested", "route": "wp", "label": "",
     "points": [(1462, _row(2)), (1510, _row(2)), (1510, _row(0)), (1608, _row(0))]},
    {"src": "loc_done",   "dst": "rel_requested", "route": "wp", "label": "",
     "points": [(1462, _row(6)), (1550, _row(6)), (1550, _row(0) + 15), (1608, _row(0) + 15)]},
    {"src": "games_done", "dst": "rel_requested", "route": "wp", "label": "",
     "points": [(890, _row(7) + 21), (1960, _row(7) + 21), (1960, _row(0)), (1892, _row(0))]},
]

# ── Vertical compaction ─────────────────────────────────────────────────────────
# The coordinates above are transcribed at a comfortable pitch; SCALE_Y squeezes the
# whole diagram vertically (nodes, edge points, headers, canvas) around ANCHOR_Y so
# arrows stay aligned. Lower SCALE_Y = tighter rows. Horizontal layout is untouched.
SCALE_Y = 0.55
ANCHOR_Y = 58


def _sy(y):
    return round(ANCHOR_Y + (y - ANCHOR_Y) * SCALE_Y)


for _n in NODES.values():
    _n["cy"] = _sy(_n["cy"])

for _sp in SPACES:
    _sp["hy"] = _sy(_sp["hy"])
    if "sub_y" in _sp:
        _sp["sub_y"] = _sy(_sp["sub_y"])

for _e in EDGES:
    if "points" in _e:
        _e["points"] = [(px, _sy(py)) for (px, py) in _e["points"]]
    if "label_xy" in _e:
        _lx, _ly = _e["label_xy"]
        _e["label_xy"] = (_lx, _sy(_ly))

CANVAS_H = _sy(CANVAS_H)

# ── Icons ───────────────────────────────────────────────────────────────────────
# Each value is the inner markup of a 0 0 24 24 SVG, drawn with stroke="currentColor"
# so the generator can colour it via the parent <g>. Feather-style single-path glyphs.
ICONS = {
    "play":         '<path d="M6 4l14 8-14 8V4z"/>',
    "search":       '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    "x-circle":     '<circle cx="12" cy="12" r="9"/><path d="M15 9l-6 6M9 9l6 6"/>',
    "check-circle": '<path d="M22 11.1V12a10 10 0 11-5.9-9.1"/><path d="M22 4L12 14.01l-3-3"/>',
    "list":         '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    "sliders":      '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
    "eye":          '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    "calendar":     '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M3 10h18M8 2v4M16 2v4"/>',
    "hash":         '<path d="M4 9h16M4 15h16M10 3L8 21M16 3l-2 18"/>',
    "doc":          '<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/>',
    "code":         '<path d="M16 18l6-6-6-6M8 6l-6 6 6 6"/>',
    "users":        '<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>',
    "box":          '<path d="M21 8l-9-5-9 5 9 5 9-5zM3 8v8l9 5 9-5V8M12 13v8"/>',
    "check":        '<path d="M20 6L9 17l-5-5"/>',
    "clipboard":    '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2"/>',
    "loader":       '<path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.2 16.2l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.2 7.8l2.8-2.8"/>',
    "translate":    '<path d="M4 5h7M9 3v2c0 4-2 7-5 9M5 9c0 3 3 5 6 6M13 21l4-9 4 9M16.5 17h5"/>',
    "edit":         '<path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>',
    "inbox":        '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z"/>',
    "cloud":        '<path d="M18 10h-1.26A8 8 0 109 20h9a5 5 0 000-10z"/>',
    "send":         '<path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>',
    "gamepad":      '<path d="M6 12h4M8 10v4M15 11h.01M18 13h.01"/><path d="M17.32 5H6.68a4 4 0 00-3.98 3.59c-.6 5.5-.5 6.41 1.3 6.41 1.5 0 2-1 3-2.5h9.4c1 1.5 1.5 2.5 3 2.5 1.8 0 1.9-.91 1.3-6.41A4 4 0 0017.32 5z"/>',
    "shield":       '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "globe":        '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 010 20 15 15 0 010-20z"/>',
    "rocket":       '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 00-2.91-.09z"/><path d="M12 15l-3-3a22 22 0 012-3.95A12.88 12.88 0 0122 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 01-4 2z"/>',
    "lightbulb":    '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 006 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6M10 22h4"/>',
}
