import os
import logging
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import time

load_dotenv()

class JiraV3Client:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JiraV3Client, cls).__new__(cls)
            cls._instance.setup()
        return cls._instance

    def setup(self):
        base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
        email = os.getenv("JIRA_USER_EMAIL")
        token = os.getenv("JIRA_API_TOKEN")
        
        # Determine domain if a full URL was provided
        if "://" in base_url:
            domain = base_url.split("://")[1]
        else:
            domain = base_url

        self.base_url = f"https://{domain}/rest/api"
        self.auth = HTTPBasicAuth(email, token)
        
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })


def update_issue(issue_key, fields: dict):
    """PUT /rest/api/3/issue/{key} to update fields (Jira accepts partial field updates via PUT)."""
    client = JiraV3Client()
    url = f"{client.base_url}/3/issue/{issue_key}"
    
    payload = {"fields": fields}
    
    try:
        response = client.session.put(url, json=payload, timeout=10)
        if response.status_code == 204:
            logging.info(f"Updated Jira issue {issue_key}")
            return True
        else:
            logging.error(f"Error updating {issue_key}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logging.error(f"Jira API connection error: {e}")
        return False

def add_comment(issue_key, body: str, internal: bool = False):
    """POST /rest/servicedeskapi/request/{issueIdOrKey}/comment for true JSM internal notes."""
    client = JiraV3Client()
    
    # JSM API is slightly different from Platform API
    url = f"{client.base_url.replace('/rest/api', '/rest/servicedeskapi')}/request/{issue_key}/comment"
    
    # JSM API uses "public": false for internal notes
    payload = {
        "body": body,
        "public": not internal
    }
    
    try:
        response = client.session.post(url, json=payload, timeout=10)
        if response.status_code == 201:
            logging.info(f"Added {'internal note' if internal else 'public comment'} to {issue_key}")
            return True
        else:
            logging.error(f"Error adding comment to {issue_key}: {response.status_code} - {response.text}")
            return _add_comment_fallback(issue_key, body, internal)
    except Exception as e:
        logging.error(f"JSM API connection error: {e}")
        return _add_comment_fallback(issue_key, body, internal)

def _add_comment_fallback(issue_key, body, internal):
    """Fallback to standard Jira Platform API v2."""
    logging.info(f"Using Platform API fallback for {issue_key}")
    client = JiraV3Client()
    url = f"{client.base_url}/2/issue/{issue_key}/comment"
    payload = {"body": body}
    if internal:
        # Standard fallback visibility
        payload["visibility"] = {"type": "role", "value": "Service Desk Team"}
    
    try:
        response = client.session.post(url, json=payload, timeout=10)
        return response.status_code == 201
    except:
        return False

def trigger_automation(webhook_url, issue_keys):
    """Triggers a Jira Automation rule via webhook."""
    if not webhook_url:
        return False
    
    payload = {"issues": issue_keys}
    
    try:
        # Automation webhook doesn't need Jira auth, so use basic requests
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code in [200, 201, 202, 204]:
            logging.info(f"Triggered automation: {webhook_url}")
            return True
        else:
            logging.error(f"Error triggering automation: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logging.error(f"Automation webhook connection error: {e}")
        return False

def get_issue(issue_key):
    """GET /rest/api/3/issue/{key}."""
    client = JiraV3Client()
    url = f"{client.base_url}/3/issue/{issue_key}"
    try:
        response = client.session.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def get_comments(issue_key):
    """GET /rest/api/3/issue/{key}/comment."""
    client = JiraV3Client()
    url = f"{client.base_url}/3/issue/{issue_key}/comment"
    try:
        response = client.session.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get("comments", [])
        return []
    except:
        return []

def get_issue_links(issue_key):
    """GET /rest/api/3/issue/{key}?fields=issuelinks to find linked tickets."""
    client = JiraV3Client()
    url = f"{client.base_url}/3/issue/{issue_key}?fields=issuelinks"
    
    try:
        response = client.session.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("fields", {}).get("issuelinks", [])
        return []
    except Exception as e:
        print(f"Jira API connection error (links): {e}")
        return []

def search_issues(jql, fields=None, max_results=50):
    """Standardized search using POST /search/jql as per Jira v3 skill."""
    client = JiraV3Client()
    url = f"{client.base_url}/3/search/jql"
    all_issues = []
    next_page_token = None

    while True:
        payload = {
            "jql": jql,
            "fields": fields or ["summary", "aggregatetimespent"],
            "maxResults": max_results
        }
        if next_page_token:
            payload["nextPageToken"] = next_page_token

        try:
            response = client.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            all_issues.extend(data.get("issues", []))
            
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
            
            # Stability delay
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Jira API search error: {e}")
            break
            
    return all_issues

def transition_issue(issue_key, status):
    """GET transitions, find by status name (case-insensitive), POST transition."""
    client = JiraV3Client()
    
    transitions_url = f"{client.base_url}/3/issue/{issue_key}/transitions"
    try:
        response = client.session.get(transitions_url, timeout=10)
        if response.status_code != 200:
            logging.error(f"Error fetching transitions for {issue_key}: {response.status_code} - {response.text}")
            return False
            
        transitions = response.json().get("transitions", [])
        transition_id = None
        for t in transitions:
            if t.get("name", "").lower() == status.lower():
                transition_id = t.get("id")
                break
                
        if not transition_id:
            logging.error(f"Transition '{status}' not found for {issue_key}")
            return False
            
        payload = {"transition": {"id": transition_id}}
        post_response = client.session.post(transitions_url, json=payload, timeout=10)
        if post_response.status_code == 204:
            logging.info(f"Transitioned {issue_key} to {status}")
            return True
        else:
            logging.error(f"Error transitioning {issue_key}: {post_response.status_code} - {post_response.text}")
            return False
            
    except Exception as e:
        logging.error(f"Jira API connection error (transition): {e}")
        return False

def add_watcher(issue_key, email):
    """POST /rest/api/3/issue/{key}/watchers with email as plain JSON string body."""
    client = JiraV3Client()
    url = f"{client.base_url}/3/issue/{issue_key}/watchers"
    
    try:
        response = client.session.post(url, json=email, timeout=10)
        if response.status_code == 204:
            logging.info(f"Added watcher {email} to {issue_key}")
            return True
        else:
            logging.error(f"Error adding watcher {email} to {issue_key}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logging.error(f"Jira API connection error (add_watcher): {e}")
        return False
