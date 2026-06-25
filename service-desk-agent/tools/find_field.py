import os
import requests
from requests.auth import HTTPBasicAuth

# C1 Credentials to fetch field list (read from environment)
DOMAIN = os.environ.get("JIRA_DOMAIN", "vvortech.atlassian.net")
EMAIL = os.environ.get("JIRA_EMAIL", "")
TOKEN = os.environ.get("JIRA_API_TOKEN", "")

def find_field_id(field_name):
    url = f"https://{DOMAIN}/rest/api/3/field"
    auth = HTTPBasicAuth(EMAIL, TOKEN)
    headers = {"Accept": "application/json"}

    response = requests.get(url, auth=auth, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return

    fields = response.json()
    for field in fields:
        if field['name'].lower() == field_name.lower():
            print(f"FOUND: Name='{field['name']}', ID='{field['id']}'")
            return field['id']
    
    print(f"Field '{field_name}' not found.")
    return None

if __name__ == "__main__":
    url = f"https://{DOMAIN}/rest/api/3/field"
    auth = HTTPBasicAuth(EMAIL, TOKEN)
    headers = {"Accept": "application/json"}

    response = requests.get(url, auth=auth, headers=headers)
    if response.status_code == 200:
        fields = response.json()
        print("Fields containing 'game':")
        for field in fields:
            if 'game' in field['name'].lower():
                print(f"Name: {field['name']}, ID: {field['id']}, Custom: {field.get('custom')}")
    else:
        print(f"Error: {response.status_code} - {response.text}")

