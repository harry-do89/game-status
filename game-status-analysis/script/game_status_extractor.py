"""
Game Status extractor.

Fetches every ticket in the five game-production "spaces" (Jira projects) and
writes result/game_status_tickets.csv. The generator buckets each ticket by
(Space, Status) to fill the flow-diagram node counts and the click-through lists.

Spaces (from config.toml → cfg["spaces"]):
  ID   → IDEAS          GAME → GAMES         CER → CERTIFICATION
  LOC  → LOCALIZATION   RM   → RELEASE

Full fetch by default; incremental fetch when SINCE_DATE env var is set
(adds `AND updated >= "..."` per project and upserts into the CSV by Ticket).
"""

import requests
import pandas as pd
import time
import os
import re
import sys
import json
from pathlib import Path
from requests.auth import HTTPBasicAuth

# ---------------------------------------------------------
# LOAD config (root .env + this board's config.toml)
# ---------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config_loader
_cfg = config_loader.apply(__file__)

# Forward hand-off mapping (ID→GAME, GAME→CER/LOC/RM, CER/LOC→RM) lives with the flow def.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scratch"))
from graph_layout import NEXT_SPACES

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------
VERSION = "2026-06-16-v1"

DOMAIN    = os.environ["JIRA_DOMAIN"]
EMAIL     = os.environ["JIRA_EMAIL"]
API_TOKEN = os.environ["JIRA_API_TOKEN"]
BASE_URL  = os.environ.get("JIRA_BASE_URL", f"https://{DOMAIN}")

DEFAULT_SPACES = ["ID", "GAME", "CER", "LOC", "RM"]
SPACES = [str(s).strip() for s in (_cfg.get("spaces") or DEFAULT_SPACES) if str(s).strip()]

EXPORT_PATH    = os.path.join("result", "game_status_tickets.csv")
LIMITS_PATH    = os.path.join("result", "game_status_limits.json")
ACTUALS_PATH   = os.path.join("result", "game_status_actuals.json")
SUBSTAGE_PATH  = os.path.join("result", "game_status_substages.json")

# Pipeline stages whose entered/exited dates the overview's delay model needs.
GAME_STAGES = [
    "Planned", "Math", "Contract Alignment", "Development",
    "Integration QC", "Optimization", "Packaging", "Done",
]

# Development sub-task discipline labels, matched (case-insensitive, first match
# wins) against the sub-task summary. Tune after inspecting real sub-tasks.
SUBSTAGE_KEYWORDS = [
    ("BE",       r"\b(be|backend|back[\s-]?end)\b"),
    ("BO",       r"\b(bo|backoffice|back[\s-]?office)\b"),
    ("Platform", r"\b(platform)\b"),
    ("FE",       r"\b(fe|frontend|front[\s-]?end)\b"),
    ("Math",     r"\b(math|maths|rng)\b"),
]


def label_substage(summary: str) -> str:
    """Return a discipline label (BE/BO/Platform/FE/Math) for a sub-task summary, or ""."""
    s = (summary or "").lower()
    for label, pattern in SUBSTAGE_KEYWORDS:
        if re.search(pattern, s):
            return label
    return ""


# ---------------------------------------------------------
# JIRA CLIENT
# ---------------------------------------------------------
class JiraClient:
    def __init__(self, domain, email, api_token):
        self.host = f"https://{domain}"
        self.base_url = f"https://{domain}/rest/api/3"
        self.auth = HTTPBasicAuth(email, api_token)
        self.headers = {"Accept": "application/json"}
        self._last_http_error = None

    def _jql_search(self, jql: str, fields: list) -> list:
        url = f"{self.base_url}/search/jql"
        issues = []
        next_page_token = None
        max_results = 50

        while True:
            payload = {"jql": jql, "fields": fields, "maxResults": max_results}
            if next_page_token:
                payload["nextPageToken"] = next_page_token

            response = requests.post(
                url, headers=self.headers, auth=self.auth, json=payload, timeout=30
            )

            if response.status_code != 200:
                msg = f"Jira API error {response.status_code}: {response.text[:300]}"
                print(f"ERROR: {msg}", flush=True)
                self._last_http_error = msg
                break

            data = response.json()
            batch = data.get("issues", [])
            issues.extend(batch)
            total_count = data.get("total", "Unknown")
            print(f"    (Retrieved {len(issues)} issues so far. Jira total: {total_count})", flush=True)

            next_page_token = data.get("nextPageToken")
            if not next_page_token or len(batch) == 0:
                break

            time.sleep(0.5)

        print(f"  Fetch complete: {len(issues)} issues", flush=True)
        return issues

    def get_project_tickets(self, project_key: str, since_date: str = None) -> list:
        jql = f'project = "{project_key}"'
        if since_date:
            jql += f' AND updated >= "{since_date}"'
        jql += " ORDER BY created DESC"
        fields = [
            "summary", "status", "assignee", "created", "updated",
            "priority", "issuetype", "parent", "issuelinks", "subtasks",
            "customfield_10664",   # Game Type (Project/Game Type)
            "customfield_10728",   # Wishful date
            "customfield_10862",   # Market
            "customfield_10866",   # Batch
            "customfield_10825",   # Game Studio
            "customfield_11023",   # Game Category
            "duedate",             # Due Date
        ]
        return self._jql_search(jql, fields)

    def fetch_changelog_actuals(self, keys: list) -> dict:
        """Return {key: {stage: {entered, exited}}} from each ticket's status changelog.

        Mirrors server.py's /api/ticket/<key>/changelog parsing, but in bulk at
        extract time so the overview can classify every GAME ticket without a live
        call. Best-effort: a per-ticket failure is logged and skipped.
        """
        actuals = {}
        for i, key in enumerate(keys):
            try:
                events, start_at = [], 0
                while True:
                    url = f"{self.base_url}/issue/{key}/changelog"
                    r = requests.get(
                        url, auth=self.auth, headers=self.headers,
                        params={"startAt": start_at, "maxResults": 100}, timeout=30,
                    )
                    if r.status_code != 200:
                        print(f"  ⚠ changelog {key}: HTTP {r.status_code}", flush=True)
                        break
                    data = r.json()
                    for entry in data.get("values", []):
                        ts = entry.get("created", "")
                        for item in entry.get("items", []):
                            if item.get("field") == "status":
                                events.append({
                                    "created": ts,
                                    "from": item.get("fromString", ""),
                                    "to":   item.get("toString", ""),
                                })
                    if data.get("isLast", True):
                        break
                    start_at += len(data.get("values", [])) or 100

                events.sort(key=lambda e: e["created"])
                stage_times: dict = {}
                for ev in events:
                    frm, to, ts = ev["from"], ev["to"], ev["created"]
                    if to in GAME_STAGES:
                        stage_times.setdefault(to, {})["entered"] = ts
                    if frm in GAME_STAGES and "exited" not in stage_times.get(frm, {}):
                        stage_times.setdefault(frm, {})["exited"] = ts
                if stage_times:
                    actuals[key] = stage_times
            except Exception as exc:
                print(f"  ⚠ changelog fetch failed for {key}: {exc}", flush=True)
            if (i + 1) % 10 == 0:
                print(f"    (changelog {i + 1}/{len(keys)})", flush=True)
            time.sleep(0.5)
        return actuals

    def fetch_substages(self, parents: list) -> dict:
        """Return {parent_key: [{label, entered, exited, eta}]} for GAME sub-tasks.

        For each GAME parent we read its full `subtasks` list (so a parent's set is
        always complete), label each child by summary keyword, and pull the child's
        own fields + status changelog in one expand call:
          entered = first status transition (work started; created date if none)
          exited  = transition into the current status when it is Done-category, else None
          eta     = the sub-task's Jira Due Date.
        Best-effort: a per-child failure is logged and skipped.
        """
        out: dict = {}
        for p in parents:
            pkey = p["key"]
            children = (p.get("fields", {}).get("subtasks") or [])
            rows = []
            for child in children:
                ckey = child.get("key", "")
                csummary = (child.get("fields", {}) or {}).get("summary", "")
                label = label_substage(csummary)
                if not ckey or not label:
                    continue
                try:
                    url = f"{self.base_url}/issue/{ckey}"
                    r = requests.get(
                        url, auth=self.auth, headers=self.headers,
                        params={"expand": "changelog", "fields": "summary,duedate,status,created"},
                        timeout=30,
                    )
                    if r.status_code != 200:
                        print(f"  ⚠ substage {ckey}: HTTP {r.status_code}", flush=True)
                        continue
                    data = r.json()
                    f = data.get("fields", {})
                    status_obj = f.get("status") or {}
                    status_name = status_obj.get("name", "")
                    status_cat = (status_obj.get("statusCategory") or {}).get("name", "")
                    created = f.get("created", "")
                    eta = str(f.get("duedate") or "")[:10] or None

                    events = []
                    for entry in data.get("changelog", {}).get("histories", []):
                        ts = entry.get("created", "")
                        for item in entry.get("items", []):
                            if item.get("field") == "status":
                                events.append({"created": ts, "to": item.get("toString", "")})
                    events.sort(key=lambda e: e["created"])

                    entered = events[0]["created"] if events else created
                    exited = None
                    if status_cat == "Done":
                        done_evs = [e for e in events if e["to"] == status_name]
                        exited = done_evs[-1]["created"] if done_evs else (events[-1]["created"] if events else None)

                    rows.append({"label": label, "entered": entered, "exited": exited, "eta": eta})
                    time.sleep(0.4)
                except Exception as exc:
                    print(f"  ⚠ substage fetch failed for {ckey}: {exc}", flush=True)
            if rows:
                out[pkey] = rows
        return out

    def fetch_limits(self, projects: list) -> dict:
        """Read WIP limits from each project's agile board column constraints.

        Returns {project_key: {status_name: max_int}} for columns that have a `max`
        set. Projects without a board (e.g. CER/LOC) are simply absent — the
        generator falls back to config.toml overrides, then a default. Best-effort:
        any failure is logged and skipped so it never breaks the ticket export.
        """
        # Resolve status id -> name once (global status table).
        status_names = {}
        try:
            r = requests.get(f"{self.base_url}/status", headers=self.headers, auth=self.auth, timeout=30)
            if r.status_code == 200:
                for s in r.json():
                    status_names[str(s["id"])] = s["name"]
                statuses_file = os.path.join("result", "jira_statuses.json")
                with open(statuses_file, "w", encoding="utf-8") as f:
                    json.dump(status_names, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"  ⚠ limits: status-name fetch failed: {exc}", flush=True)

        limits = {}
        for proj in projects:
            try:
                br = requests.get(
                    f"{self.host}/rest/agile/1.0/board",
                    params={"projectKeyOrId": proj},
                    headers=self.headers, auth=self.auth, timeout=30,
                )
                boards = br.json().get("values", []) if br.status_code == 200 else []
                if not boards:
                    continue
                bid = boards[0]["id"]
                cr = requests.get(
                    f"{self.host}/rest/agile/1.0/board/{bid}/configuration",
                    headers=self.headers, auth=self.auth, timeout=30,
                )
                if cr.status_code != 200:
                    continue
                cols = cr.json().get("columnConfig", {}).get("columns", [])
                pmap = {}
                for c in cols:
                    mx = c.get("max")
                    if mx in (None, ""):
                        continue
                    for s in c.get("statuses", []):
                        name = status_names.get(str(s.get("id")))
                        if name:
                            pmap[name] = int(mx)
                if pmap:
                    limits[proj] = pmap
                time.sleep(0.3)
            except Exception as exc:
                print(f"  ⚠ limits: fetch failed for {proj}: {exc}", flush=True)
        return limits


def forward_clone_key(issuelinks, project: str) -> str:
    """Return the key of a downstream "Cloners" clone, or "" if none.

    A ticket is handed off when it has a "Cloners" link to a ticket in one of its
    NEXT_SPACES. The upstream original carries the outward link and the downstream
    clone an inward link, so we match on the *linked issue's project* (not direction):
    e.g. GAME-1→CER-1 excludes GAME-1 (CER ∈ next[GAME]); CER-1's inward link to GAME-1
    does NOT exclude CER-1 (GAME ∉ next[CER]).
    """
    targets = NEXT_SPACES.get(project, ())
    if not targets:
        return ""
    for link in issuelinks or []:
        if (link.get("type") or {}).get("name") != "Cloners":
            continue
        linked = link.get("outwardIssue") or link.get("inwardIssue") or {}
        linked_key = linked.get("key", "")
        if linked_key and linked_key.split("-")[0] in targets:
            return linked_key
    return ""


# ---------------------------------------------------------
# MAIN PROCESSING
# ---------------------------------------------------------

def process_game_status_data(since_date: str = None):
    """
    Full fetch if since_date is None.
    Incremental fetch if since_date provided — upsert into existing CSV by Ticket.
    """
    mode = f"incremental (updated >= {since_date})" if since_date else "full"
    print(f"\n--- game_status_extractor.py {VERSION} — Extraction [{mode}] ---", flush=True)
    print(f"Spaces: {', '.join(SPACES)}", flush=True)

    client = JiraClient(DOMAIN, EMAIL, API_TOKEN)

    # ── Phase 1: fetch all spaces ──────────────────────────────────────────────
    all_raw: dict = {}
    for project in SPACES:
        print(f"\nFetching space {project}...", flush=True)
        tickets = client.get_project_tickets(project, since_date=since_date)
        if getattr(client, "_last_http_error", None):
            print(f"FATAL: Jira request failed for space {project} — {client._last_http_error}", flush=True)
            sys.exit(1)
        print(f"  Space {project}: {len(tickets)} tickets", flush=True)
        all_raw[project] = tickets

    # ── Phase 2: compute which RM tickets have GAME children ──────────────────
    # Check the RM ticket's own `subtasks` list for any key starting with "GAME-".
    # GAME tickets do not reference RM tickets, so we only look RM-side.
    rm_with_game_children: set = set()
    for issue in all_raw.get("RM", []):
        key = issue["key"]
        for child in (issue.get("fields", {}).get("subtasks") or []):
            if (child.get("key") or "").startswith("GAME-"):
                rm_with_game_children.add(key)
                break

    print(f"\nRM tickets with GAME children: {len(rm_with_game_children)}", flush=True)

    # ── Phase 3: emit records ──────────────────────────────────────────────────
    records = []
    for project in SPACES:
        tickets = all_raw[project]

        # First pass: collect max-updated from subtasks keyed by their parent.
        child_max_updated: dict = {}
        for issue in tickets:
            f = issue.get("fields", {})
            issuetype = f.get("issuetype") or {}
            if issuetype.get("subtask", False):
                parent_key = (f.get("parent") or {}).get("key")
                if parent_key:
                    updated = f.get("updated", "")
                    if updated > child_max_updated.get(parent_key, ""):
                        child_max_updated[parent_key] = updated

        # Second pass: emit only non-subtask issues with effective updated date.
        for issue in tickets:
            f = issue.get("fields", {})
            issuetype = f.get("issuetype") or {}
            if issuetype.get("subtask", False):
                continue
            key = issue["key"]
            own_updated = f.get("updated", "")
            effective_updated = max(own_updated, child_max_updated.get(key, "")) if own_updated else child_max_updated.get(key, "")
            status_obj = f.get("status") or {}
            assignee_raw = f.get("assignee")
            assignee = (
                assignee_raw.get("displayName", "Unassigned")
                if isinstance(assignee_raw, dict)
                else "Unassigned"
            )
            priority_obj = f.get("priority") or {}

            gt_raw = f.get("customfield_10664") or {}
            game_type = gt_raw.get("value", "") if isinstance(gt_raw, dict) else str(gt_raw or "")

            wishful_raw = f.get("customfield_10728") or ""
            wishful_date = str(wishful_raw)[:10] if wishful_raw else ""

            mkt_raw = f.get("customfield_10862") or {}
            market = mkt_raw.get("value", "") if isinstance(mkt_raw, dict) else str(mkt_raw or "")

            batch_raw = f.get("customfield_10866") or {}
            batch = batch_raw.get("value", "") if isinstance(batch_raw, dict) else str(batch_raw or "")

            studio_raw = f.get("customfield_10825") or {}
            game_studio = studio_raw.get("value", "") if isinstance(studio_raw, dict) else str(studio_raw or "")

            cat_raw = f.get("customfield_11023") or {}
            game_category = cat_raw.get("value", "") if isinstance(cat_raw, dict) else str(cat_raw or "")

            cloned_forward = forward_clone_key(f.get("issuelinks"), project)

            has_game_child = ""
            if project == "RM":
                has_game_child = "Yes" if key in rm_with_game_children else "No"

            due_raw = f.get("duedate") or ""
            due_date = str(due_raw)[:10] if due_raw else ""

            records.append({
                "Ticket":          key,
                "Space":           project,
                "Status":          status_obj.get("name", "N/A"),
                "Status Category": (status_obj.get("statusCategory") or {}).get("name", ""),
                "Summary":         f.get("summary", ""),
                "Assignee":        assignee,
                "Priority":        priority_obj.get("name", ""),
                "Game Type":       game_type,
                "Wishful Date":    wishful_date,
                "Market":          market,
                "Batch":           batch,
                "Game Studio":     game_studio,
                "Game Category":   game_category,
                "Created Date":    f.get("created", ""),
                "Updated Date":    effective_updated,
                "URL":             f"{BASE_URL}/browse/{key}",
                "Cloned Forward":  cloned_forward,
                "Has Game Child":  has_game_child,
                "Due Date":        due_date,
            })

    df_new = pd.DataFrame(records)

    # GAME tickets touched by this run — the only keys whose changelog we refetch.
    touched_game_keys = (
        df_new[df_new["Space"] == "GAME"]["Ticket"].tolist() if not df_new.empty else []
    )
    # Parent (non-subtask) GAME issue objects for those keys — carry the full
    # `subtasks` list the sub-stage fetch needs.
    _touched = set(touched_game_keys)
    touched_game_issues = [
        issue for issue in all_raw.get("GAME", [])
        if issue["key"] in _touched
        and not ((issue.get("fields", {}).get("issuetype") or {}).get("subtask", False))
    ]

    # --- SHORT-CIRCUIT: incremental fetch returned nothing new ---
    if df_new.empty:
        if since_date and os.path.exists(EXPORT_PATH):
            print(f"No updated tickets since {since_date}. Returning existing CSV unchanged.")
            return pd.read_csv(EXPORT_PATH), [], []
        print("No tickets retrieved.")
        return df_new, [], []

    # --- MERGE: upsert into existing CSV for incremental mode ---
    if since_date and os.path.exists(EXPORT_PATH):
        print(f"Merging {len(df_new)} updated tickets into existing CSV...", flush=True)
        df_existing = pd.read_csv(EXPORT_PATH)
        df_existing = df_existing[~df_existing["Ticket"].isin(df_new["Ticket"])]
        df = pd.concat([df_existing, df_new], ignore_index=True)
        print(f"Merged total: {len(df)} tickets ({len(df_new)} updated/new).", flush=True)
    else:
        df = df_new

    return df, touched_game_keys, touched_game_issues


# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    os.makedirs("result", exist_ok=True)

    since = os.environ.get("SINCE_DATE")
    df, touched_game_keys, touched_game_issues = process_game_status_data(since_date=since)

    if not df.empty:
        print("\n===========================================")
        print("FINISHED GAME STATUS EXTRACTION. SAMPLE DATA:")
        print("===========================================")
        print(f"Row count: {len(df)}")
        print(f"Spaces: {df['Space'].value_counts().to_dict()}")
        print(df.head(10).to_string())

        df.to_csv(EXPORT_PATH, index=False)
        print(f"\nExported to {EXPORT_PATH}")
    else:
        print("\nNo data retrieved.")

    # --- WIP limits from Jira board column constraints (best-effort) ---
    try:
        client = JiraClient(DOMAIN, EMAIL, API_TOKEN)
        limits = client.fetch_limits(SPACES)
        with open(LIMITS_PATH, "w", encoding="utf-8") as f:
            json.dump(limits, f, ensure_ascii=False, indent=2)
        print(f"Wrote limits to {LIMITS_PATH}: {limits}")
    except Exception as exc:
        print(f"⚠ Could not write limits: {exc}")

    # --- GAME stage actuals from changelog, for the overview delay model (best-effort) ---
    # Refetch only the GAME tickets touched by this run; merge over any existing file so
    # incremental refreshes stay cheap (one changelog call per updated GAME ticket).
    try:
        if touched_game_keys:
            existing = {}
            if since and os.path.exists(ACTUALS_PATH):
                with open(ACTUALS_PATH, encoding="utf-8") as f:
                    existing = json.load(f)
            print(f"\nFetching changelog for {len(touched_game_keys)} GAME ticket(s)...", flush=True)
            client = JiraClient(DOMAIN, EMAIL, API_TOKEN)
            fresh = client.fetch_changelog_actuals(touched_game_keys)
            existing.update(fresh)
            with open(ACTUALS_PATH, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            print(f"Wrote stage actuals for {len(existing)} GAME ticket(s) to {ACTUALS_PATH}")
        else:
            print("No GAME tickets touched — leaving stage actuals unchanged.")
    except Exception as exc:
        print(f"⚠ Could not write stage actuals: {exc}")

    # --- Development sub-stage timeline from GAME sub-tasks (best-effort) ---
    # Refetch only the GAME parents touched by this run; merge per-parent over any
    # existing file so incremental refreshes stay cheap.
    try:
        if touched_game_issues:
            existing = {}
            if since and os.path.exists(SUBSTAGE_PATH):
                with open(SUBSTAGE_PATH, encoding="utf-8") as f:
                    existing = json.load(f)
            print(f"\nFetching sub-stages for {len(touched_game_issues)} GAME parent(s)...", flush=True)
            client = JiraClient(DOMAIN, EMAIL, API_TOKEN)
            fresh = client.fetch_substages(touched_game_issues)
            existing.update(fresh)
            with open(SUBSTAGE_PATH, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            print(f"Wrote sub-stages for {len(existing)} GAME parent(s) to {SUBSTAGE_PATH}")
        else:
            print("No GAME parents touched — leaving sub-stages unchanged.")
    except Exception as exc:
        print(f"⚠ Could not write sub-stages: {exc}")
