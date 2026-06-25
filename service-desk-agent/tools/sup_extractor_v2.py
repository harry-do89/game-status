import requests
import pandas as pd
import json
import base64
import time
import os
from requests.auth import HTTPBasicAuth

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

# The GAME_ID field is a custom field in Jira. 
# customfield_10660 was verified as 'Game ID' in extractor.py
GAME_ID_CUSTOM_FIELD = "customfield_10660" 
REQUEST_TYPE_CUSTOM_FIELD = "customfield_10010"

# Credentials for C1 (Primary Tenant) — read from environment, never hardcode.
DOMAIN = os.environ.get("JIRA_DOMAIN", "vvortech.atlassian.net")
EMAIL = os.environ.get("JIRA_EMAIL", "")
API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "SUP")

# ---------------------------------------------------------
# CORE LOGIC
# ---------------------------------------------------------

class JiraClient:
    def __init__(self, domain, email, api_token):
        self.base_url = f"https://{domain}/rest/api/3"
        self.auth = HTTPBasicAuth(email, api_token)
        self.headers = {"Accept": "application/json"}

    def _jql_search(self, jql: str, fields: list) -> list:
        """Helper to run JQL queries using the modern cursor-based /search/jql endpoint."""
        url = f"{self.base_url}/search/jql"
        issues = []
        next_page_token = None
        max_results = 50

        while True:
            payload = {
                "jql": jql,
                "fields": fields,
                "maxResults": max_results
            }
            if next_page_token:
                payload["nextPageToken"] = next_page_token
                
            response = requests.post(url, headers=self.headers, auth=self.auth, json=payload, timeout=30)
            
            if response.status_code != 200:
                print(f"Error fetching data: {response.status_code} - {response.text}")
                break

            data = response.json()
            batch = data.get("issues", [])
            issues.extend(batch)
            
            total_count = data.get("total", "Unknown")
            print(f"    (Retrieved {len(issues)} issues. Total: {total_count})")

            # Cursor-based pagination: check for nextPageToken
            next_page_token = data.get("nextPageToken")
            if not next_page_token or len(batch) == 0:
                break
            
            # Rate limit protection
            time.sleep(0.5)

        return issues

    def get_sup_tickets(self, project_key: str) -> list:
        jql = f'project = "{project_key}" ORDER BY created DESC'
        fields = [
            "summary", 
            GAME_ID_CUSTOM_FIELD, 
            REQUEST_TYPE_CUSTOM_FIELD,
            "status",
            "created", 
            "resolutiondate", 
            "issuelinks",
            "description",
            "updated",
            "statuscategorychangedate",
            "issuetype"
        ]
        return self._jql_search(jql, fields)

    def get_jsm_field_config(self, project_key: str) -> dict:
        """Fetch all request types and their fields for a JSM project."""
        # 1. Get Service Desk ID
        desk_url = f"https://{DOMAIN}/rest/servicedeskapi/servicedesk"
        response = requests.get(desk_url, auth=self.auth, headers=self.headers)
        desk_id = None
        if response.status_code == 200:
            for desk in response.json().get("values", []):
                if desk.get("projectKey") == project_key:
                    desk_id = desk["id"]
                    break
        
        if not desk_id:
            print(f"Service Desk not found for project {project_key}")
            return {}

        config = {}
        # 2. Get Request Types
        rt_url = f"https://{DOMAIN}/rest/servicedeskapi/servicedesk/{desk_id}/requesttype"
        rt_response = requests.get(rt_url, auth=self.auth, headers=self.headers)
        if rt_response.status_code == 200:
            for rt in rt_response.json().get("values", []):
                rt_id = rt["id"]
                rt_name = rt["name"]
                
                # 3. Get Fields for this Request Type
                f_url = f"https://{DOMAIN}/rest/servicedeskapi/servicedesk/{desk_id}/requesttype/{rt_id}/field"
                f_response = requests.get(f_url, auth=self.auth, headers=self.headers)
                if f_response.status_code == 200:
                    fields = f_response.json().get("requestTypeFields", [])
                    config[rt_name] = [
                        {"name": f.get("name"), "id": f.get("fieldId"), "required": f.get("required")} 
                        for f in fields
                    ]
        return config

def process_sup_data():
    print(f"\n--- Starting SUP Data Extraction ---")
    client = JiraClient(DOMAIN, EMAIL, API_TOKEN)
    
    print(f"Fetching tickets for project {PROJECT_KEY}...")
    
    # --- FIELD CONFIG EXPORT ---
    print(f"Exporting field configuration for {PROJECT_KEY}...")
    field_config = client.get_jsm_field_config(PROJECT_KEY)
    if field_config:
        docs_dir = "docs"
        os.makedirs(docs_dir, exist_ok=True)
        config_path = os.path.join(docs_dir, "SUP_Request_Type_Fields.md")
        with open(config_path, "w") as f:
            f.write(f"# SUP Request Type Field Configuration\n\n")
            f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for rt_name, fields in field_config.items():
                f.write(f"## {rt_name}\n")
                f.write(f"| Field Name | Field ID | Required |\n")
                f.write(f"| :--- | :--- | :--- |\n")
                for field in fields:
                    f.write(f"| {field['name']} | `{field['id']}` | {'Yes' if field['required'] else 'No'} |\n")
                f.write("\n")
        print(f"Field configuration exported to {config_path}")

    tickets = client.get_sup_tickets(PROJECT_KEY)
    print(f"Found {len(tickets)} tickets.")

    records = []

    for ticket in tickets:
        ticket_key = ticket["key"]
        fields = ticket.get("fields", {})
        summary = fields.get("summary", "")
        created_date = fields.get("created", "")
        resolved_date = fields.get("resolutiondate", "")
        updated_date = fields.get("updated", "")
        status_change_date = fields.get("statuscategorychangedate", "")
        issue_type = fields.get("issuetype", {}).get("name", "N/A")
        
        # Safely access Status
        status = fields.get("status", {}).get("name", "N/A")
        
        # Safely access Game ID
        game_id = fields.get(GAME_ID_CUSTOM_FIELD)
        if isinstance(game_id, dict):
            game_id = game_id.get("value") or game_id.get("name") or str(game_id)
        if game_id is None:
            game_id = "N/A"

        # Safely access Request Type
        request_type = fields.get(REQUEST_TYPE_CUSTOM_FIELD)
        if isinstance(request_type, dict):
            # Request Type in JSM is often a nested object
            request_type = request_type.get("requestType", {}).get("name") or request_type.get("value") or request_type.get("name") or str(request_type)
        if request_type is None:
            request_type = "N/A"

        # Extract linked tasks and identify clones
        linked_tasks = []
        clone_key = None
        links = fields.get("issuelinks", [])
        for link in links:
            link_type = link.get("type", {}).get("name")
            if link_type == "Cloners":
                if "outwardIssue" in link:
                    # SUP clones TO another issue (this is the one we want)
                    clone_key = link["outwardIssue"]["key"]
                elif "inwardIssue" in link:
                    # SUP is cloned FROM another issue
                    pass
            
            if "outwardIssue" in link:
                linked_tasks.append(f"To: {link['outwardIssue']['key']}")
            elif "inwardIssue" in link:
                linked_tasks.append(f"From: {link['inwardIssue']['key']}")
        
        linked_tasks_str = ", ".join(linked_tasks) if linked_tasks else "None"

        # Safely access Description (V3 API returns ADF format, but we'll try to get plain text if possible 
        # or just handle the first text node for simple themes)
        description_raw = fields.get("description")
        description_text = ""
        if isinstance(description_raw, dict) and "content" in description_raw:
            try:
                # Basic extraction of text nodes from ADF
                for block in description_raw["content"]:
                    if "content" in block:
                        for item in block["content"]:
                            if item.get("type") == "text":
                                description_text += item.get("text", "") + " "
            except:
                description_text = str(description_raw)
        else:
            description_text = str(description_raw or "")

        records.append({
            "SUP Ticket": ticket_key,
            "Issue Type": issue_type,
            "Summary": summary,
            "Status": status,
            "Game ID": game_id,
            "Request Type": request_type,
            "Linked Tasks": linked_tasks_str,
            "Clone Ticket": clone_key,
            "Created Date": created_date,
            "Resolved Date": resolved_date,
            "Updated Date": updated_date,
            "Status Category Change Date": status_change_date,
            "Description": description_text.strip()
        })

    df = pd.DataFrame(records)
    
    # --- ENRICHMENT: Fetch Clone Created Dates ---
    clone_keys = [k for k in df["Clone Ticket"] if k and k != "None"]
    if clone_keys:
        print(f"Fetching creation dates for {len(set(clone_keys))} cloned tickets...")
        # Split into batches of 50 to avoid JQL length limits
        clone_data_map = {}
        for i in range(0, len(clone_keys), 50):
            batch = list(set(clone_keys[i:i+50]))
            jql = f"key in ({','.join(batch)})"
            batch_issues = client._jql_search(jql, ["created"])
            for issue in batch_issues:
                clone_data_map[issue["key"]] = issue["fields"].get("created")
        
        df["Clone Created Date"] = df["Clone Ticket"].map(clone_data_map)
    else:
        df["Clone Created Date"] = None

    return df

# ---------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------
if __name__ == "__main__":
    EXPORT_DIR = "result"
    os.makedirs(EXPORT_DIR, exist_ok=True)

    df = process_sup_data()
    
    if not df.empty:
        print("\n\n===========================================")
        print("FINISHED SUP EXTRACTION. SAMPLE DATA:")
        print("===========================================")
        print(f"Row count: {len(df)}")
        print(df.head(10).to_string()) # Show sample

        # Export
        export_path = os.path.join(EXPORT_DIR, "sup_tickets_export_v2.csv")
        df.to_csv(export_path, index=False)
        print(f"\nExported to {export_path}")
    else:
        print("\nNo data retrieved.")
