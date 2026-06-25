import os
import sys
import warnings
import logging

# Suppress noisy deprecation warnings from third-party libs
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*NotOpenSSLWarning.*")
warnings.filterwarnings("ignore", message=".*urllib3.*")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
# Silence urllib3 and google warning noise at log level too
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("google").setLevel(logging.ERROR)

from dotenv import load_dotenv
load_dotenv()

import re
import time
import json
import threading
from pathlib import Path
from flask import Flask, request, jsonify, Response

# Load root .env + this component's config.toml (MODE, derived Jira aliases)
# BEFORE importing gemini/jira, which read creds at import time.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config_loader
config_loader.apply(__file__)

import gemini
import utils
import gchat
import reporter
import jira
import pic_config
from admin import admin_bp, mode_state

app = Flask(__name__)
app.register_blueprint(admin_bp)

# ── SUP Analysis dashboard (mounted at /sup) ──────────────────────────────────
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sup-analysis"))
    from server import sup_bp
    app.register_blueprint(sup_bp, url_prefix="/sup")
    logging.info("SUP dashboard mounted at /sup")
except Exception as _e:
    logging.warning(f"SUP dashboard not loaded: {_e}")

# ── PI (Production Incident) dashboard (mounted at /pi) ──────────────────────
try:
    import importlib.util as _ilu
    _pi_server_path = Path(__file__).resolve().parents[2] / "production-incident-analysis" / "server.py"
    _spec = _ilu.spec_from_file_location("pi_server", str(_pi_server_path))
    _pi_server = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_pi_server)
    app.register_blueprint(_pi_server.pi_bp, url_prefix="/pi")
    logging.info("PI dashboard mounted at /pi")
except Exception as _e:
    logging.warning(f"PI dashboard not loaded: {_e}")

# ── Verticals dashboard (mounted at /verticals) ───────────────────────────────
try:
    import importlib.util as _ilu
    _vtx_server_path = Path(__file__).resolve().parents[2] / "pact_verticals_analysis" / "server.py"
    _spec = _ilu.spec_from_file_location("pact_verticals_server", str(_vtx_server_path))
    _pact_server = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_pact_server)
    app.register_blueprint(_pact_server.verticals_bp)
    logging.info("Verticals dashboard mounted at /verticals")
except Exception as _e:
    logging.warning(f"Verticals dashboard not loaded: {_e}")

# ── Recurring Issues dashboard (mounted at /maintain) ──────────────────────────
try:
    import importlib.util as _ilu
    _maintain_server_path = Path(__file__).resolve().parents[2] / "system-maintain-analysis" / "server.py"
    _spec = _ilu.spec_from_file_location("maintain_server", str(_maintain_server_path))
    _maintain_server = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_maintain_server)
    app.register_blueprint(_maintain_server.maintain_bp, url_prefix="/maintain")
    logging.info("Recurring Issues dashboard mounted at /maintain")
except Exception as _e:
    logging.warning(f"Recurring Issues dashboard not loaded: {_e}")

# ── Game Status dashboard (mounted at /game-status) ────────────────────────────
try:
    import importlib.util as _ilu
    _gs_server_path = Path(__file__).resolve().parents[2] / "game-status-analysis" / "server.py"
    _spec = _ilu.spec_from_file_location("game_status_server", str(_gs_server_path))
    _gs_server = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_gs_server)
    app.register_blueprint(_gs_server.game_status_bp, url_prefix="/game-status")
    logging.info("Game Status dashboard mounted at /game-status")
except Exception as _e:
    logging.warning(f"Game Status dashboard not loaded: {_e}")

# ── Board Priority Queue dashboard (mounted at /priority-queue) ─────────────────
try:
    import importlib.util as _ilu
    _pq_server_path = Path(__file__).resolve().parents[2] / "board-priority-queue" / "server.py"
    _spec = _ilu.spec_from_file_location("priority_server", str(_pq_server_path))
    _pq_server = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_pq_server)
    app.register_blueprint(_pq_server.priority_bp, url_prefix="/priority-queue")
    logging.info("Board Priority Queue dashboard mounted at /priority-queue")
except Exception as _e:
    logging.warning(f"Board Priority Queue dashboard not loaded: {_e}")


@app.route("/dashboard")
def dashboard():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Engineering Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', sans-serif; background: #0a1628; color: #f0f9ff; height: 100vh; display: flex; flex-direction: column; }
  .tab-bar { display: flex; background: #0f2035; border-bottom: 1px solid #1e3a5f; padding: 0 24px; gap: 4px; align-items: flex-end; flex-shrink: 0; }
  .tab { padding: 12px 28px; cursor: pointer; font-size: 0.95rem; font-weight: 600; color: #94a3b8; border: 1px solid transparent; border-bottom: none; border-radius: 8px 8px 0 0; transition: all 0.15s; user-select: none; }
  .tab:hover { color: #f0f9ff; background: rgba(14,165,233,0.08); }
  .tab.active { color: #38bdf8; background: #0a1628; border-color: #1e3a5f; margin-bottom: -1px; }
  .frames { flex: 1; position: relative; }
  iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: none; display: none; }
  iframe.active { display: block; }
</style>
</head>
<body>
<div class="tab-bar">
  <div class="tab active" onclick="switchTab(this,'sup-frame','/sup/')">📊 SUP Analysis</div>
  <div class="tab" onclick="switchTab(this,'vtx-frame','/verticals')">🗂 Verticals</div>
  <div class="tab" onclick="switchTab(this,'pi-frame','/pi/')">🚨 Production Incident</div>
  <div class="tab" onclick="switchTab(this,'maintain-frame','/maintain/')">🛠 Recurring Issues</div>
  <div class="tab" onclick="switchTab(this,'gs-frame','/game-status/')">🎮 Game Status</div>
  <div class="tab" onclick="switchTab(this,'pq-frame','/priority-queue/')">🎯 Priority Queue</div>
</div>
<div class="frames">
  <iframe id="sup-frame" class="active" src="/sup/"></iframe>
  <iframe id="vtx-frame" data-src="/verticals"></iframe>
  <iframe id="pi-frame" data-src="/pi/"></iframe>
  <iframe id="maintain-frame" data-src="/maintain/"></iframe>
  <iframe id="gs-frame" data-src="/game-status/"></iframe>
  <iframe id="pq-frame" data-src="/priority-queue/"></iframe>
</div>
<script>
  function switchTab(tab, frameId, src) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('iframe').forEach(f => f.classList.remove('active'));
    tab.classList.add('active');
    const frame = document.getElementById(frameId);
    // Lazy-load: set src on first click so charts render in a visible iframe
    if (!frame.src || frame.src === window.location.href) {
      frame.src = frame.dataset.src || src;
    }
    frame.classList.add('active');
  }
</script>
</body>
</html>"""
    return Response(html, mimetype="text/html")


def process_triage(data):
    """Background process for /triage."""
    start_time = time.time()
    issue_key = data.get("issue_key", "UNKNOWN")
    try:
        # 1. Load config
        pic_cfg = pic_config.load_pic_config()
        special_rules = pic_config.load_special_rules()

        # 2. Sanitise inputs
        summary = utils.sanitise(data.get("summary", ""))
        description = utils.sanitise(data.get("description", ""))
        reporter_name = utils.sanitise(data.get("reporter", ""))
        raw_ticket_type = data.get("ticket_type")
        ticket_type = utils.format_request_type(utils.sanitise(raw_ticket_type or "N/A"))
        if not raw_ticket_type or ticket_type == "N/A":
            _issue = jira.get_issue(issue_key)
            if _issue:
                _f = _issue.get("fields", {})
                _fetched = (
                    (_f.get("customfield_10010") or {}).get("requestType", {}).get("name")
                    or _f.get("issuetype", {}).get("name")
                )
                if _fetched:
                    ticket_type = utils.format_request_type(_fetched)
                    logging.info(f"[{issue_key}] ticket_type fetched from Jira: {repr(ticket_type)}")
        logging.info(f"[{issue_key}] ticket_type raw={repr(raw_ticket_type)} formatted={repr(ticket_type)}")
        game_name = utils.sanitise(data.get("game_name", "N/A"))
        environment = utils.sanitise(data.get("environment", "N/A"))

        ticket_key = issue_key
        raw_game_id = utils.sanitise(data.get("game_id", ""))
        # Multiple game IDs separated by ; or , — use the first one only
        game_id = re.split(r"[;,]", raw_game_id)[0].strip() if raw_game_id else ""

        # 3. Prepare prompt with XML fencing
        prompt = utils.load_prompt("triage",
            special_rules=json.dumps(special_rules),
            pic_config=json.dumps(pic_cfg),
            ticket_key=ticket_key,
            game_id=game_id,
            ticket_type=ticket_type,
            game_name=game_name,
            environment=environment,
            summary=summary,
            description=description,
            reporter=reporter_name
        )

        # 4. Call Gemini
        logging.debug(f"[{issue_key}] triage prompt:\n{prompt}")
        result_text = gemini.ask(prompt)
        logging.debug(f"[{issue_key}] Gemini raw response: {result_text}")
        duration_ms = int((time.time() - start_time) * 1000)
        result = utils.parse_gemini_json(result_text)
        result["request_type"] = ticket_type

        if ticket_type.lower() in ("production incident", "production support"):
            result["priority"] = "Critical"
            logging.info(f"[{issue_key}] Priority overridden to Critical (ticket_type={ticket_type})")

        mode = mode_state["value"]
        actions = []
        logging.info(f"[{issue_key}] Processing in mode: {mode}")

        if mode == "on":
            if result.get("declined") is True:
                logging.info(f"[{issue_key}] Ticket declined by agent rule")
                decline_message = result.get("decline_message", "Ticket declined by automated rule.")
                jira.add_comment(issue_key, decline_message, internal=False)
                jira.transition_issue(issue_key, "Decline")
                reporter.send("triage", mode, issue_key, summary, result, ["ticket_declined", "comment_posted"], duration_ms)
                return

            # 5. Update Jira
            logging.info(f"[{issue_key}] Updating Jira fields")
            
            assigned_pic_name = None
            assigned_pic_email = None
            assigned_account_id = None
            assigned_team_id = None
            assigned_team_name = None
            used_fallback = False

            fallback = pic_cfg.get("fallback", {})
            devops_fallback = fallback.get("devops", {})
            destination_board = str(result.get("destination_board", "")).upper()
            is_devops = ticket_type.lower() == "devops support" or destination_board == "DEVOPS"
            if is_devops and devops_fallback.get("email"):
                assigned_pic_name = devops_fallback.get("pic_name")
                assigned_pic_email = devops_fallback.get("email")
                assigned_account_id = devops_fallback.get("account_id")

            if not assigned_pic_email:
                by_game_id = pic_cfg.get("by_game_id", {})
                game_rule = by_game_id.get(game_id) if game_id else None
                if game_rule:
                    assigned_pic_name = game_rule.get("pic_name")
                    assigned_pic_email = game_rule.get("pic_email")
                    assigned_account_id = game_rule.get("pic_account_id")
                    assigned_team_id = game_rule.get("team_id")
                    assigned_team_name = game_rule.get("team_name")
                else:
                    general_fallback = fallback.get("general", {})
                    assigned_pic_name = general_fallback.get("pic_name")
                    assigned_pic_email = general_fallback.get("email")
                    assigned_account_id = general_fallback.get("account_id")
                    used_fallback = True

            if assigned_team_name:
                result["team_name"] = assigned_team_name

            fields = {
                "priority": {"name": result.get("priority", "Medium")},
            }
            if assigned_account_id:
                fields["assignee"] = {"accountId": assigned_account_id}
            elif assigned_pic_email:
                logging.warning(f"[{issue_key}] No account_id in config for {assigned_pic_email}, assignee not set")

            if jira.update_issue(issue_key, fields):
                if assigned_team_name:
                    actions.append(f"Assigned to Team: {assigned_team_name}")
                pic_label = assigned_pic_name or assigned_pic_email
                if pic_label:
                    actions.append(f"PIC in SUP: {pic_label}")
                if used_fallback:
                    actions.append(f"⚠️ Game ID '{game_id}' not found in config — assigned to general fallback PIC")
                
            if result.get("team_email"):
                jira.add_watcher(issue_key, result.get("team_email"))

            # 6. Add Internal Comment with Triage Note
            logging.info(f"[{issue_key}] Adding internal comment")
            fallback_note = f"\n⚠️ **Game ID '{game_id}' not found in config — assigned to general fallback PIC.**" if used_fallback else ""
            comment = f"[PACT Agent] 🤖 **Triage Decision**\n\n**Note:** {result.get('triage_note')}\n**Team:** {result.get('suggested_team')}\n**Board:** {result.get('destination_board')}\n**Confidence:** {result.get('confidence')}{fallback_note}"
            if jira.add_comment(issue_key, comment, internal=True):
                actions.append("Triage internal comment added")

            gchat.send_card(
                title="🤖 Triage Complete",
                subtitle=issue_key,
                facts={
                    "Request Type": ticket_type,
                    "Priority": result.get("priority", "N/A"),
                    "PIC": assigned_pic_name or assigned_pic_email or "N/A",
                    "Board": result.get("destination_board", "N/A")
                }
            )

            # 7. Trigger Automation Webhooks
            board = str(result.get("destination_board", "")).upper()
            triggered = False
            logging.info(f"[{issue_key}] Checking automation for board: {board}")
            if "PORTFOLIO" in board:
                logging.info(f"[{issue_key}] Triggering Portfolio clone")
                if jira.trigger_automation(os.getenv("JIRA_WEBHOOK_PORTFOLIO"), [issue_key]):
                    triggered = True
            elif "BUG" in board:
                logging.info(f"[{issue_key}] Triggering Bug Tracker clone")
                if jira.trigger_automation(os.getenv("JIRA_WEBHOOK_BUG"), [issue_key]):
                    triggered = True
            elif "DEVOPS" in board:
                logging.info(f"[{issue_key}] Triggering DevOps clone")
                if jira.trigger_automation(os.getenv("JIRA_WEBHOOK_DEVOPS"), [issue_key]):
                    triggered = True
            elif "RNG" in board:
                logging.info(f"[{issue_key}] Triggering RNG Task clone (cheat tool inaccessible)")
                if jira.trigger_automation(os.getenv("JIRA_WEBHOOK_RNG_TASK"), [issue_key]):
                    triggered = True

            if triggered:
                logging.info(f"[{issue_key}] Waiting 5s for clone creation")
                time.sleep(5)
                links = jira.get_issue_links(issue_key)
                logging.debug(f"[{issue_key}] Found {len(links)} links")
                clone_key = "Unknown"
                for link in links:
                    outward = link.get("outwardIssue", {})
                    inward = link.get("inwardIssue", {})
                    key = outward.get("key") or inward.get("key", "")
                    if any(prefix in key for prefix in ["PACT-", "BUG-", "DEVOPS-", "RNG-"]):
                        clone_key = key
                        break
                actions.append(f"Jira Automation: Triggered Clone ({clone_key})")
                
                if clone_key != "Unknown":
                    clone_fields = {}
                    if clone_key.startswith("BUG-"):
                        if assigned_team_id:
                            clone_fields["customfield_10001"] = assigned_team_id
                            clone_fields["assignee"] = None
                        elif assigned_account_id:
                            clone_fields["assignee"] = {"accountId": assigned_account_id}
                    elif clone_key.startswith("RNG-"):
                        if assigned_team_id:
                            clone_fields["customfield_10001"] = assigned_team_id
                            clone_fields["assignee"] = None
                        elif assigned_account_id:
                            clone_fields["assignee"] = {"accountId": assigned_account_id}
                    else:
                        if assigned_account_id:
                            clone_fields["assignee"] = {"accountId": assigned_account_id}
                    
                    if clone_fields:
                        logging.info(f"[{issue_key}] Updating clone {clone_key} with fields: {clone_fields}")
                        jira.update_issue(clone_key, clone_fields)

        elif mode == "test":
            if result.get("declined") is True:
                actions.append("[MOCK] Post declined comment (public)")
                actions.append("[MOCK] Transition issue to 'Decline'")
                reporter.send("triage", mode, issue_key, summary, result, actions, duration_ms)
                return
                
            assigned_pic_name = None
            assigned_pic_email = None
            assigned_team_id = None
            assigned_team_name = None
            used_fallback = False

            fallback = pic_cfg.get("fallback", {})
            devops_fallback = fallback.get("devops", {})
            destination_board = str(result.get("destination_board", "")).upper()
            is_devops = ticket_type.lower() == "devops support" or destination_board == "DEVOPS"
            if is_devops and devops_fallback.get("email"):
                assigned_pic_name = devops_fallback.get("pic_name")
                assigned_pic_email = devops_fallback.get("email")

            if not assigned_pic_email:
                by_game_id = pic_cfg.get("by_game_id", {})
                game_rule = by_game_id.get(game_id) if game_id else None
                if game_rule:
                    assigned_pic_name = game_rule.get("pic_name")
                    assigned_pic_email = game_rule.get("pic_email")
                    assigned_team_id = game_rule.get("team_id")
                    assigned_team_name = game_rule.get("team_name")
                else:
                    general_fallback = fallback.get("general", {})
                    assigned_pic_name = general_fallback.get("pic_name")
                    assigned_pic_email = general_fallback.get("email")
                    used_fallback = True

            if assigned_team_name:
                result["team_name"] = assigned_team_name

            board = str(result.get("destination_board", "")).upper()
            pic_label = assigned_pic_name or assigned_pic_email or "N/A"
            actions.append(f"[MOCK] Update Jira (Priority: {result.get('priority', 'N/A')}, Assignee: {pic_label})")
            if result.get("team_email"):
                actions.append(f"[MOCK] Add Watcher: {result.get('team_email')}")
            actions.append("[MOCK] Post internal triage note")
            actions.append("[MOCK] Send GChat card")
            if "PORTFOLIO" in board:
                actions.append("[MOCK] Trigger Jira Automation: PACT PORTFOLIO Clone (PACT-999)")
                if assigned_pic_email:
                    actions.append(f"[MOCK] Update cloned PACT-999 with Assignee: {assigned_pic_email}")
            elif "BUG" in board:
                actions.append("[MOCK] Trigger Jira Automation: BUG TRACKER Clone (BUG-999)")
                if assigned_team_id:
                    actions.append(f"[MOCK] Update cloned BUG-999 with Team ID: {assigned_team_id}")
                elif assigned_pic_email:
                    actions.append(f"[MOCK] Update cloned BUG-999 with Assignee: {assigned_pic_email}")
            elif "DEVOPS" in board:
                actions.append("[MOCK] Trigger Jira Automation: DEVOPS Clone (DEVOPS-999)")
                if assigned_pic_email:
                    actions.append(f"[MOCK] Update cloned DEVOPS-999 with Assignee: {assigned_pic_email}")
            elif "RNG" in board:
                actions.append("[MOCK] Trigger Jira Automation: RNG Task Clone via JIRA_WEBHOOK_RNG_TASK (RNG-999)")
                if assigned_pic_email:
                    actions.append(f"[MOCK] Update cloned RNG-999 with Assignee: {assigned_pic_email}")
            if used_fallback:
                actions.append(f"⚠️ Game ID '{game_id}' not found in config — assigned to general fallback PIC")
        else:
            actions.append("suppressed")

        # 7. Report
        print(f"INFO: Sending final report for {issue_key}...", flush=True)
        reporter.send("triage", mode, issue_key, summary, result, actions, duration_ms)

    except Exception as e:
        print(f"ERROR in process_triage: {e}", flush=True)
        import traceback; traceback.print_exc()
        duration_ms = int((time.time() - start_time) * 1000)
        reporter.send("triage", mode_state["value"], issue_key, data.get("summary", "N/A"), {}, [], duration_ms, error=str(e))


def process_scan(data):
    """Background process for /scan."""
    start_time = time.time()
    issue_key = data.get("issue_key", "UNKNOWN")
    try:
        text = utils.sanitise(data.get("text", ""))
        prompt = utils.load_prompt("scan", text=text)
        logging.debug(f"[{issue_key}] scan prompt:\n{prompt}")
        result_text = gemini.ask(prompt)
        duration_ms = int((time.time() - start_time) * 1000)
        result = utils.parse_gemini_json(result_text)

        mode = mode_state["value"]
        actions = []

        if mode == "on" and result.get("flagged"):
            reasons = ", ".join(result.get("reasons", []))
            comment = f"[PACT Agent] ⚠️ **Sensitive content detected**\n\n**Risk:** {result.get('risk_level')}\n**Reasons:** {reasons}"
            if jira.add_comment(issue_key, comment, internal=True):
                actions.append("Internal flag comment added")
            gchat.send_card(
                title="🚨 Sensitive Content Flagged",
                subtitle=issue_key,
                facts={"Risk": result.get("risk_level"), "Reasons": reasons}
            )
            actions.append("Team lead notified")
        elif mode == "test" and result.get("flagged"):
            actions.append(f"[MOCK] Post internal sensitive content warning (Risk: {result.get('risk_level')})")
            actions.append("[MOCK] Notify team lead via GChat")
        else:
            actions.append("suppressed or not flagged")

        reporter.send("scan", mode, issue_key, text[:100], result, actions, duration_ms)
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        reporter.send("scan", mode_state["value"], issue_key, "N/A", {}, [], duration_ms, error=str(e))


def process_rewrite(data):
    """Background process for /rewrite."""
    start_time = time.time()
    issue_key = data.get("issue_key", "UNKNOWN")
    try:
        summary = utils.sanitise(data.get("summary", ""))
        description = utils.sanitise(data.get("description", ""))
        comments = utils.sanitise(data.get("comments", ""))

        prompt = utils.load_prompt("rewrite",
            summary=summary,
            description=description,
            comments=comments
        )
        logging.debug(f"[{issue_key}] rewrite prompt:\n{prompt}")
        result_text = gemini.ask(prompt)
        duration_ms = int((time.time() - start_time) * 1000)
        result = utils.parse_gemini_json(result_text)

        mode = mode_state["value"]
        actions = []

        if mode == "on":
            criteria = "\n".join([f"- {c}" for c in result.get("acceptance_criteria", [])])
            comment = f"[PACT Agent] 🛠 **Technical Rewrite**\n\n**Dev Summary:** {result.get('dev_summary')}\n\n**Dev Description:**\n{result.get('dev_description')}\n\n**Acceptance Criteria:**\n{criteria}"
            if jira.add_comment(issue_key, comment, internal=True):
                actions.append("Technical rewrite posted as internal comment")
        elif mode == "test":
            actions.append("[MOCK] Post technical rewrite as internal comment")
        else:
            actions.append("suppressed")

        reporter.send("rewrite", mode, issue_key, summary, result, actions, duration_ms)
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        reporter.send("rewrite", mode_state["value"], issue_key, data.get("summary", "N/A"), {}, [], duration_ms, error=str(e))


def process_summarise(data):
    """Background process for /summarise."""
    start_time = time.time()
    issue_key = data.get("issue_key", "UNKNOWN")
    try:
        summary = utils.sanitise(data.get("summary", ""))
        board = utils.sanitise(data.get("board", ""))
        priority = utils.sanitise(data.get("priority", ""))
        status = utils.sanitise(data.get("status", ""))
        assignee = utils.sanitise(data.get("assignee", ""))
        reporter_name = utils.sanitise(data.get("reporter", ""))
        last_updated = data.get("last_updated", data.get("updated", ""))
        current_time = time.strftime("%Y-%m-%d %H:%M")
        last_comment = utils.sanitise(data.get("last_comment", ""))
        last_comment_author = utils.sanitise(data.get("last_comment_author", ""))
        last_comment_date = data.get("last_comment_date", "")

        prompt = utils.load_prompt("summarise",
            ticket_key=issue_key,
            board=board,
            priority=priority,
            status=status,
            summary=summary,
            assignee=assignee,
            reporter=reporter_name,
            last_updated=last_updated,
            current_time=current_time,
            last_comment=last_comment,
            last_comment_author=last_comment_author,
            last_comment_date=last_comment_date
        )
        logging.debug(f"[{issue_key}] summarise prompt:\n{prompt}")
        result_text = gemini.ask(prompt)
        duration_ms = int((time.time() - start_time) * 1000)
        result = utils.parse_gemini_json(result_text)

        mode = mode_state["value"]
        actions = []

        if mode == "on" and result.get("is_stale"):
            comment = f"[PACT Agent] 👋 **Stale Ticket Nudge**\n\n{result.get('recommended_action')}"
            if jira.add_comment(issue_key, comment):
                actions.append("Nudge comment added")
            gchat.send_card(
                title=f"{result.get('urgency_label', '⏳ Stale Ticket')} Nudge",
                subtitle=issue_key,
                facts={
                    "Stall Reason": result.get("stall_reason"),
                    "Inactive (biz hrs)": result.get("inactive_business_hours"),
                    "Last Activity": result.get("last_activity_summary"),
                    "Recommended Action": result.get("recommended_action")
                }
            )
            actions.append("Ops digest sent")
        elif mode == "on":
            actions.append("Not stale — no action taken")
        elif mode == "test" and result.get("is_stale"):
            actions.append(f"[MOCK] Post nudge comment ({result.get('urgency_label', 'Stale')})")
            actions.append("[MOCK] Send stale ticket summary to GChat")
        elif mode == "test":
            actions.append("Not stale — no action taken")
        else:
            actions.append("suppressed")

        reporter.send("summarise", mode, issue_key, summary, result, actions, duration_ms)
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        reporter.send("summarise", mode_state["value"], issue_key, data.get("summary", "N/A"), {}, [], duration_ms, error=str(e))


def process_detect(data):
    """Background process for /detect."""
    start_time = time.time()
    issue_key = data.get("issue_key", "UNKNOWN")
    try:
        parent_summary = utils.sanitise(data.get("parent_summary", ""))
        today = data.get("today", "")
        raw_linked = data.get("linked_issues", [])
        linked_issues = [
            {k: utils.sanitise(v) if isinstance(v, str) else v for k, v in item.items()}
            if isinstance(item, dict) else utils.sanitise(item) if isinstance(item, str) else item
            for item in raw_linked
        ] if isinstance(raw_linked, list) else []

        prompt = utils.load_prompt("detect",
            parent_summary=parent_summary,
            today=today,
            linked_issues=linked_issues
        )
        logging.debug(f"[{issue_key}] detect prompt:\n{prompt}")
        result_text = gemini.ask(prompt)
        duration_ms = int((time.time() - start_time) * 1000)
        result = utils.parse_gemini_json(result_text)

        mode = mode_state["value"]
        actions = []

        if mode == "on" and result.get("action_needed"):
            comment = f"[PACT Agent] 🔴 **Linked Issue Reminder**\n\n{result.get('reminder_message')}"
            if jira.add_comment(issue_key, comment):
                actions.append("Reminder comment added to parent")
            gchat.send_card(
                title="⚠️ Linked Issue Reminder",
                subtitle=issue_key,
                facts={
                    "Blocked": ", ".join(result.get("blocked_issues", [])),
                    "Message": result.get("reminder_message")
                }
            )
            actions.append("Developer notified via Chat")
        elif mode == "on":
            actions.append("No action needed")
        elif mode == "test" and result.get("action_needed"):
            blocked = ", ".join(result.get("blocked_issues", []))
            actions.append(f"[MOCK] Post linked issue reminder comment (blocked: {blocked})")
            actions.append("[MOCK] Notify developer via GChat")
        elif mode == "test":
            actions.append("Not blocked — no action taken")
        else:
            actions.append("suppressed")

        reporter.send("detect", mode, issue_key, data.get("parent_summary", "N/A"), result, actions, duration_ms)
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        reporter.send("detect", mode_state["value"], issue_key, data.get("parent_summary", "N/A"), {}, [], duration_ms, error=str(e))


@app.route('/triage', methods=['POST'])
def triage():
    utils.verify_key(request)
    mode = mode_state["value"]
    data = request.json
    issue_key = data.get("issue_key", "UNKNOWN")
    if mode == "off":
        reporter.send("triage", "off", issue_key, data.get("summary", "N/A"), {}, [], 0)
        return jsonify({"status": "offline"}), 202
    threading.Thread(target=process_triage, args=(data,)).start()
    return jsonify({"status": "accepted", "issue_key": issue_key}), 202


@app.route('/scan', methods=['POST'])
def scan():
    utils.verify_key(request)
    mode = mode_state["value"]
    data = request.json
    issue_key = data.get("issue_key", "UNKNOWN")
    if mode == "off":
        reporter.send("scan", "off", issue_key, data.get("text", "N/A")[:100], {}, [], 0)
        return jsonify({"status": "offline"}), 202
    threading.Thread(target=process_scan, args=(data,)).start()
    return jsonify({"status": "accepted", "issue_key": issue_key}), 202


@app.route('/rewrite', methods=['POST'])
def rewrite():
    utils.verify_key(request)
    mode = mode_state["value"]
    data = request.json
    issue_key = data.get("issue_key", "UNKNOWN")
    if mode == "off":
        reporter.send("rewrite", "off", issue_key, data.get("summary", "N/A"), {}, [], 0)
        return jsonify({"status": "offline"}), 202
    threading.Thread(target=process_rewrite, args=(data,)).start()
    return jsonify({"status": "accepted", "issue_key": issue_key}), 202


@app.route('/summarise', methods=['POST'])
def summarise():
    utils.verify_key(request)
    mode = mode_state["value"]
    data = request.json
    issue_key = data.get("issue_key", "UNKNOWN")
    if mode == "off":
        reporter.send("summarise", "off", issue_key, data.get("summary", "N/A"), {}, [], 0)
        return jsonify({"status": "offline"}), 202
    threading.Thread(target=process_summarise, args=(data,)).start()
    return jsonify({"status": "accepted", "issue_key": issue_key}), 202


@app.route('/detect', methods=['POST'])
def detect():
    utils.verify_key(request)
    mode = mode_state["value"]
    data = request.json
    issue_key = data.get("issue_key", "UNKNOWN")
    if mode == "off":
        reporter.send("detect", "off", issue_key, data.get("parent_summary", "N/A"), {}, [], 0)
        return jsonify({"status": "offline"}), 202
    threading.Thread(target=process_detect, args=(data,)).start()
    return jsonify({"status": "accepted", "issue_key": issue_key}), 202


@app.route('/admin/triage', methods=['POST'])
def admin_triage():
    """Manually trigger triage for a specific issue key (missed during downtime)."""
    utils.verify_key(request)
    data = request.json
    issue_key = data.get("issue_key")
    
    if not issue_key:
        return jsonify({"error": "issue_key is required"}), 400

    logging.info(f"Admin: Manually triggering triage for {issue_key}")
    
    # Fetch issue details from Jira
    issue = jira.get_issue(issue_key)
    if not issue:
        return jsonify({"error": f"Issue {issue_key} not found in Jira"}), 404
        
    fields = issue.get("fields", {})
    
    # Extract description text (handles ADF or plain text)
    description_text = ""
    description_raw = fields.get("description")
    if isinstance(description_raw, dict) and "content" in description_raw:
        try:
            for block in description_raw["content"]:
                if "content" in block:
                    for item in block["content"]:
                        if item.get("type") == "text":
                            description_text += item.get("text", "") + " "
        except:
            description_text = str(description_raw)
    else:
        description_text = str(description_raw or "")

    # Construct payload to match what JSM webhook would send.
    # game_id is not a standard Jira field — caller must pass it in the request body if known.
    webhook_payload = {
        "issue_key": issue_key,
        "summary": fields.get("summary", ""),
        "description": description_text.strip(),
        "reporter": fields.get("reporter", {}).get("displayName", "Unknown"),
        "ticket_type": (
            (fields.get("customfield_10010") or {}).get("requestType", {}).get("name")
            or fields.get("issuetype", {}).get("name", "N/A")
        ),
        "game_name": "N/A",
        "environment": "N/A",
        "game_id": data.get("game_id", "")
    }

    # Run the standard triage process
    threading.Thread(target=process_triage, args=(webhook_payload,)).start()
    
    return jsonify({
        "status": "accepted", 
        "message": f"Manual triage triggered for {issue_key}",
        "payload_sent": webhook_payload
    }), 202


if __name__ == '__main__':
    mode = os.getenv("MODE", "off")
    print("\n" + "="*40)
    print(f"🤖 PACT AGENT STARTING UP")
    print(f"📡 ACTIVE MODE: {mode.upper()}")
    print("="*40 + "\n")
    app.run(host='0.0.0.0', port=8080)
