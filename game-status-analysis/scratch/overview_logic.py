"""
Overview logic for the Game Status "Game Production Overview" dashboard.

Pure, dependency-light functions (the presentation analogue of the other boards'
report_logic.py). The generator feeds these a list of GAME ticket dicts + the
changelog actuals map, and gets back a single `overview` dict ready to embed as
JSON and render client-side.

SINGLE SOURCE OF TRUTH for the production schedule: GAME_STAGES / STAGE_DURATIONS /
RISK_DAYS live here. shared/timeline_modal.py mirrors GAME_STAGES + STAGE_DURATIONS in
JS (TL_STAGES / TL_DURATIONS) for the per-ticket modal's estimate fallback; keep in sync.
"""

from __future__ import annotations

import datetime as _dt

# ── Production schedule constants ──────────────────────────────────────────────
# Ordered game-production pipeline. "Done" is terminal (not an active stage).
GAME_STAGES = [
    "Planned", "Math", "Contract Alignment", "Development",
    "Integration QC", "Optimization", "Packaging", "Done",
]
ACTIVE_STAGES = [s for s in GAME_STAGES if s != "Done"]

# Planned working duration of each stage, in days. Plan dates are derived
# cumulatively from a ticket's Created Date over this map.
STAGE_DURATIONS = {
    "Planned": 4, "Math": 5, "Contract Alignment": 3, "Development": 20,
    "Integration QC": 10, "Optimization": 5, "Packaging": 4, "Done": 1,
}

# A game whose current stage is planned to end within this many days is "at risk".
RISK_DAYS = 5

# Bucket identifiers used everywhere (Python + JS).
LATE, RISK, ONTRACK, DONE = "late", "risk", "ontrack", "done"


# ── Date helpers ───────────────────────────────────────────────────────────────
def _date(s):
    """Parse the leading YYYY-MM-DD of an ISO string into a date, or None."""
    if not s:
        return None
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def build_plan_dates(created):
    """{stage: (plan_start, plan_end)} accumulated from the created date."""
    start = _date(created) or _dt.date.today()
    plan = {}
    cur = start
    for stage in GAME_STAGES:
        dur = STAGE_DURATIONS.get(stage, 5)
        ps = cur
        pe = cur + _dt.timedelta(days=dur - 1)
        plan[stage] = (ps, pe)
        cur = pe + _dt.timedelta(days=1)
    return plan


def _deadline(row):
    """Effective deadline = Due Date → Wishful Date fallback."""
    return _date(row.get("due_date")) or _date(row.get("wishful_date"))


# ── Per-game classification ────────────────────────────────────────────────────
def classify_game(row, actuals, today):
    """Classify one GAME ticket into a delay bucket with a human reason.

    Returns a dict merged onto the game record:
      bucket       — late | risk | ontrack | done
      reason       — short Vietnamese reason ('' for on-track/done)
      reason_days  — the integer of days in the reason (0 if n/a)
      reason_kind  — 'flag' (late) | 'warn' (risk) | '' — drives the action icon
      deadline     — effective deadline ISO date or ''
      days_left    — days until deadline (negative = overdue), or None
    """
    status = (row.get("status") or "").strip()
    dl = _deadline(row)
    days_left = (dl - today).days if dl else None
    base = {
        "deadline": dl.isoformat() if dl else "",
        "days_left": days_left,
    }

    if status == "Done":
        return {**base, "bucket": DONE, "reason": "", "reason_days": 0, "reason_kind": ""}

    # GAME tickets parked in a non-pipeline status are treated as on-track (uncounted reason).
    if status not in ACTIVE_STAGES:
        return {**base, "bucket": ONTRACK, "reason": "", "reason_days": 0, "reason_kind": ""}

    plan = build_plan_dates(row.get("created"))
    ps, pe = plan[status]
    is_first = status == ACTIVE_STAGES[0]  # "Planned" — production hasn't started

    # When did the ticket actually enter its current stage?
    entered = _date((actuals.get(status) or {}).get("entered"))
    if entered is None and is_first:
        entered = _date(row.get("created"))  # created straight into Planned

    # 1) Past the planned end of the current stage → LATE.
    if today > pe:
        d = (today - pe).days
        if is_first:
            reason = f"not started, {d}d late"
        else:
            reason = f"{d}d past plan end"
        return {**base, "bucket": LATE, "reason": reason, "reason_days": d, "reason_kind": "flag"}

    # 2) Still within plan window — check start slippage / imminent deadline → RISK.
    if entered is not None:
        start_delay = (entered - ps).days
        if start_delay > 0:
            return {**base, "bucket": RISK, "reason": f"start {start_delay}d late",
                    "reason_days": start_delay, "reason_kind": "warn"}

    days_to_end = (pe - today).days
    if days_to_end <= RISK_DAYS:
        return {**base, "bucket": RISK, "reason": f"due in {days_to_end}d",
                "reason_days": days_to_end, "reason_kind": "warn"}

    return {**base, "bucket": ONTRACK, "reason": "", "reason_days": 0, "reason_kind": ""}


# ── Aggregators ────────────────────────────────────────────────────────────────
_BUCKET_ORDER = {LATE: 0, RISK: 1, ONTRACK: 2, DONE: 3}


def _is_active(g):
    return g["bucket"] in (LATE, RISK, ONTRACK)


def kpis(games):
    active = [g for g in games if _is_active(g)]
    late = [g for g in active if g["bucket"] == LATE]
    risk = [g for g in active if g["bucket"] == RISK]
    ontrack = [g for g in active if g["bucket"] == ONTRACK]
    return {
        "active": len(active),
        "late": len(late),
        "risk": len(risk),
        "ontrack": len(ontrack),
        "late_keys": [g["key"] for g in late],
        "risk_keys": [g["key"] for g in risk],
    }


def pipeline_health(games):
    """Count of active games per active stage, with late/risk sub-counts."""
    out = []
    for stage in ACTIVE_STAGES:
        in_stage = [g for g in games if _is_active(g) and (g.get("status") or "") == stage]
        out.append({
            "stage": stage,
            "count": len(in_stage),
            "late": sum(1 for g in in_stage if g["bucket"] == LATE),
            "risk": sum(1 for g in in_stage if g["bucket"] == RISK),
        })
    return out


def action_items(games):
    """Active late/risk games, worst-first (late before risk, larger slip first)."""
    items = [g for g in games if g["bucket"] in (LATE, RISK)]
    items.sort(key=lambda g: (_BUCKET_ORDER[g["bucket"]], -g["reason_days"]))
    return [{
        "key": g["key"],
        "status": g.get("status", ""),
        "bucket": g["bucket"],
        "reason": g["reason"],
        "reason_days": g["reason_days"],
        "reason_kind": g["reason_kind"],
    } for g in items]


def upcoming_deadlines(games, days=30):
    """Active games whose effective deadline is within `days`, soonest first."""
    out = [g for g in games
           if _is_active(g) and g["days_left"] is not None and g["days_left"] <= days]
    out.sort(key=lambda g: g["days_left"])
    return [{
        "key": g["key"],
        "summary": g.get("summary", ""),
        "studio": g.get("game_studio", ""),
        "deadline": g["deadline"],
        "days_left": g["days_left"],
        "bucket": g["bucket"],
    } for g in out]


# Field key in the game dict → label shown on the group tab.
GROUP_FIELDS = [
    ("game_studio", "Game studio"),
    ("market", "Market"),
    ("game_category", "Category"),
]

# Known option values that must always appear in a group's breakdown, even with
# zero matching tickets (e.g. a market with no active GAME tickets right now).
KNOWN_GROUP_VALUES = {
    "market": ["Nigeria", "Brazil"],
}


def group_breakdown(games, field):
    """Group ALL games (incl. Done) by `field`; per group give bucket counts + items.

    Used by both the per-group health squares and the stacked delay-bars, so it
    carries Done too. Groups sorted worst-first (late, then risk, then size).
    """
    groups = {
        name: {"name": name, "items": [], LATE: 0, RISK: 0, ONTRACK: 0, DONE: 0}
        for name in KNOWN_GROUP_VALUES.get(field, [])
    }
    for g in games:
        name = (g.get(field) or "").strip()
        bucket = g["bucket"]
        grp = groups.setdefault(name, {"name": name, "items": [],
                                       LATE: 0, RISK: 0, ONTRACK: 0, DONE: 0})
        grp["items"].append({"key": g["key"], "bucket": bucket})
        grp[bucket] += 1
    out = list(groups.values())
    for grp in out:
        grp["items"].sort(key=lambda i: _BUCKET_ORDER[i["bucket"]])
        grp["total"] = len(grp["items"])
    out.sort(key=lambda grp: (-grp[LATE], -grp[RISK], -grp["total"], grp["name"]))
    return out


def compute_overview(games_raw, actuals, today=None):
    """Top-level entry: classify every GAME ticket and assemble the overview dict.

    games_raw — list of GAME ticket dicts (key, summary, status, created, due_date,
                wishful_date, game_studio, market, game_category, batch, …).
    actuals   — {key: {stage: {entered, exited}}} from the changelog.
    """
    today = today or _dt.date.today()
    games = []
    for row in games_raw:
        g = dict(row)
        g.update(classify_game(row, actuals.get(row.get("key"), {}), today))
        games.append(g)

    groups = {label: group_breakdown(games, field) for field, label in GROUP_FIELDS}

    # Minimal per-ticket record so a card click can open the shared Gantt modal.
    by_key = {
        g["key"]: {
            "summary": g.get("summary", ""),
            "studio": g.get("game_studio", ""),
            "market": g.get("market", ""),
            "batch": g.get("batch", ""),
            "category": g.get("game_category", ""),
            "wishful": g.get("wishful_date", ""),
            "status": g.get("status", ""),
            "created": g.get("created", ""),
        }
        for g in games
    }

    return {
        "as_of": today.isoformat(),
        "kpi": kpis(games),
        "pipeline": pipeline_health(games),
        "actions": action_items(games),
        "deadlines": upcoming_deadlines(games),
        "groups": groups,
        "group_fields": [label for _, label in GROUP_FIELDS],
        "by_key": by_key,
    }
