import os
import re
import logging
import requests
import datetime
from collections import defaultdict

# Module-level state for failure tracking
failure_counts = defaultdict(int)

def record_failure(flow):
    """Increments failure count and sends critical alert if threshold reached."""
    failure_counts[flow] += 1
    if failure_counts[flow] >= 3:
        send_critical_alert(flow, failure_counts[flow])
        failure_counts[flow] = 0

def send_critical_alert(flow, count):
    """Sends a critical alert card to GChat Report space."""
    webhook_url = os.getenv("GCHAT_REPORT_WEBHOOK_URL")
    if not webhook_url:
        return

    payload = {
        "cardsV2": [{
            "cardId": "critical_alert",
            "card": {
                "header": {
                    "title": "🚨 CRITICAL — Agent Failure Threshold Reached",
                    "subtitle": f"Flow: {flow}"
                },
                "sections": [{
                    "widgets": [
                        {"textParagraph": {"text": f"<b>Failure Count:</b> {count}"}},
                        {"textParagraph": {"text": "Check Gemini status and logs immediately."}}
                    ]
                }]
            }
        }]
    }
    requests.post(webhook_url, json=payload)

def send(flow, mode, ticket_key, summary, gemini_result, actions_taken, duration_ms, error=None):
    """Sends an Agent Report Card v2 message. Always fires."""
    webhook_url = os.getenv("GCHAT_REPORT_WEBHOOK_URL")
    base_url = os.getenv("JIRA_BASE_URL", "https://vvortech.atlassian.net").rstrip("/")
    if not webhook_url:
        return

    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    if error:
        record_failure(flow)

    widgets = [
        {"textParagraph": {"text": f"<b>Ticket:</b> <a href=\"{base_url}/browse/{ticket_key}\">{ticket_key}</a>"}},
        {"textParagraph": {"text": f"<b>Summary:</b> {summary}"}}
    ]

    if mode == "off":
        widgets.append({"textParagraph": {"text": "🔴 Agent OFFLINE — request received but not processed"}})
    else:
        # Gemini Decision
        gemini_text = ""
        # Fields to omit from the report card
        _SKIP_FIELDS = {
            "declined", "ticket_key", "pic_email", "team_id",
            "team_email", "assignment_rule_used", "team_name", "category"
        }
        # Mapping internal keys to user-friendly display labels
        key_map = {
            "priority": "Priority",
            "destination_board": "Board",
            "request_type": "Request Type",
            "suggested_team": "Suggested Teams",
            "team_name": "Team Name",
            "is_production_incident": "Is Production Incident",
            "confidence": "Confidence",
            "triage_note": "Triage Note"
        }
        
        for k, v in gemini_result.items():
            if k in _SKIP_FIELDS:
                continue
            display_key = key_map.get(k, k.replace("_", " ").title())
            
            # Formatting logic
            if k == "is_production_incident" and not v:
                continue # Skip if false as requested
            
            if k == "suggested_team" and isinstance(v, str):
                # Title case first, then force specific acronyms to uppercase
                v = v.replace("_", " ").title()
                for acronym in ["Rng", "Bo"]:
                    v = v.replace(acronym, acronym.upper())
            
            gemini_text += f"<b>{display_key}:</b> {v}<br>"
            
        widgets.append({"textParagraph": {"text": f"<b>PACT Agent Decision:</b><br>{gemini_text}"}})

        # Actions Taken
        actions_text = ""
        for action in actions_taken:
            # Actions that start with ⚠️ carry their own icon — don't prepend a status icon
            if action.startswith("⚠️"):
                icon = ""
            else:
                icon = "✅" if mode == "on" else "🔕"

            # Auto-hyperlink any Jira keys (SUP-XXX, PACT-XXX, BUG-XXX)
            action_linked = re.sub(r"([A-Z]{2,}-\d+)", rf'<a href="{base_url}/browse/\1">\1</a>', action)

            actions_text += f"{icon} {action_linked}<br>" if icon else f"{action_linked}<br>"
        
        if error:
            actions_text += f"🔴 <b>Error:</b> {error}<br>"
        
        actions_text += f"⏱ <b>Duration:</b> {duration_ms}ms"
        widgets.append({"textParagraph": {"text": f"<b>Actions:</b><br>{actions_text}"}})

    payload = {
        "cardsV2": [{
            "cardId": f"report_{ticket_key}",
            "card": {
                "header": {
                    "title": "🤖 Agent Action Report",
                    "subtitle": f"Flow: {flow} | Mode: {mode.upper()} | {timestamp}"
                },
                "sections": [{"widgets": widgets}]
            }
        }]
    }

    try:
        requests.post(webhook_url, json=payload)
    except Exception as e:
        logging.error(f"Error sending Agent Report: {e}")
