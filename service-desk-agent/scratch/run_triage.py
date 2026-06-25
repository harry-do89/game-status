import os
import sys
import logging
from dotenv import load_dotenv

# Add scripts directory to path
sys.path.append(os.path.join(os.getcwd(), "scripts"))

import jira
import main
from admin import mode_state

# Configure logging to see what's happening
logging.getLogger().setLevel(logging.DEBUG)

def run_manual_triage(issue_key):
    load_dotenv()
    
    # Force mode to 'test' so we don't accidentally update Jira while testing prompt changes
    # Unless the user explicitly wants to run it in 'on' mode.
    # For verification, 'test' is safer.
    mode_state["value"] = "test"
    print(f"Running triage for {issue_key} in TEST mode")

    # Fetch issue details from Jira
    issue = jira.get_issue(issue_key)
    if not issue:
        print(f"Error: Issue {issue_key} not found.")
        return
        
    fields = issue.get("fields", {})
    
    # Extract description text
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

    # Construct payload
    webhook_payload = {
        "issue_key": issue_key,
        "summary": fields.get("summary", ""),
        "description": description_text.strip(),
        "reporter": fields.get("reporter", {}).get("displayName", "Unknown"),
        "ticket_type": fields.get("issuetype", {}).get("name", "N/A"),
        "game_name": "N/A",
        "environment": "N/A"
    }

    # Run the triage process synchronously
    main.process_triage(webhook_payload)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scratch/run_triage.py <ISSUE_KEY>")
    else:
        run_manual_triage(sys.argv[1])
