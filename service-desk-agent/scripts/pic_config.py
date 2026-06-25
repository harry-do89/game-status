import os
import time
import logging
import threading
from google.oauth2 import service_account
from googleapiclient.discovery import build

_cached_config = None
_cached_special_rules = None
_last_fetch_time = 0
CACHE_TTL = 300
_cache_lock = threading.Lock()

def get_sheets_service():
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials/jira-agent-personal-f0bd8631745a.json")
    if os.path.exists(creds_path):
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=scopes)
    else:
        import google.auth
        creds, _ = google.auth.default(scopes=scopes)
    return build('sheets', 'v4', credentials=creds)

def _parse_bool(val):
    if not val:
        return False
    return str(val).strip().upper() == "TRUE"

def fetch_data_from_sheets():
    sheet_id = os.getenv("PIC_CONFIG_SHEET_ID")
    if not sheet_id:
        raise ValueError("PIC_CONFIG_SHEET_ID env var is not set")
        
    service = get_sheets_service()
    sheet = service.spreadsheets()
    
    ranges = ["fallback!A:D", "by_game_id!A:E", "special_rules!A:C"]

    try:
        result = sheet.values().batchGet(spreadsheetId=sheet_id, ranges=ranges).execute()
        value_ranges = result.get('valueRanges', [])
    except Exception as e:
        logging.error(f"Error fetching from Google Sheets: {e}")
        raise e

    def get_rows(index):
        if index < len(value_ranges):
            vals = value_ranges[index].get('values', [])
            if vals:
                return vals[1:]
        return []

    # 1. fallback tab: A=pic_name, B=pic_email, C=pic_account_id, D=role
    #    Builds both the pics lookup dict AND fallback assignment rules
    pics = {}
    fallback = {}
    for row in get_rows(0):
        if len(row) >= 2 and row[1].strip():
            pic_name = row[0].strip() if row[0].strip() else None
            pic_email = row[1].strip()
            pic_account_id = row[2].strip() if len(row) > 2 and row[2].strip() else None
            role = row[3].strip().lower() if len(row) > 3 and row[3].strip() else None
            pics[pic_email] = {"pic_name": pic_name, "pic_account_id": pic_account_id}
            if role:
                fallback[role] = {"pic_name": pic_name, "email": pic_email, "account_id": pic_account_id}

    # 2. by_game_id: A=game_id, B=team_name, C=team_id, D=pic_email, E=active
    by_game_id = {}
    for row in get_rows(1):
        if len(row) >= 5:
            active = _parse_bool(row[4])
            if active:
                pic_email = row[3].strip() if len(row) > 3 and row[3].strip() else None
                pic = pics.get(pic_email, {})
                by_game_id[row[0].strip()] = {
                    "team_name": row[1].strip() if len(row) > 1 and row[1].strip() else None,
                    "team_id": row[2].strip() if len(row) > 2 and row[2].strip() else None,
                    "pic_email": pic_email,
                    "pic_name": pic.get("pic_name"),
                    "pic_account_id": pic.get("pic_account_id"),
                    "active": active
                }

    # 3. special_rules
    special_rules = {}
    for row in get_rows(2):
        if len(row) >= 2:
            rule_name = row[0].strip()
            enabled = _parse_bool(row[1])
            special_rules[rule_name] = enabled

    pic_config = {
        "by_game_id": by_game_id,
        "fallback": fallback
    }

    return pic_config, special_rules

def load_pic_config(force_refresh=False):
    global _cached_config, _cached_special_rules, _last_fetch_time
    with _cache_lock:
        current_time = time.time()
        if force_refresh or _cached_config is None or (current_time - _last_fetch_time > CACHE_TTL):
            try:
                _cached_config, _cached_special_rules = fetch_data_from_sheets()
                _last_fetch_time = current_time
            except Exception as e:
                if _cached_config is not None:
                    logging.warning(f"Sheets fetch failed, using cached pic_config. Error: {e}")
                else:
                    raise RuntimeError(f"No cached pic_config available and Sheets API failed: {e}") from e
    return _cached_config

def load_special_rules(force_refresh=False):
    global _cached_config, _cached_special_rules, _last_fetch_time
    with _cache_lock:
        current_time = time.time()
        if force_refresh or _cached_special_rules is None or (current_time - _last_fetch_time > CACHE_TTL):
            try:
                _cached_config, _cached_special_rules = fetch_data_from_sheets()
                _last_fetch_time = current_time
            except Exception as e:
                if _cached_special_rules is not None:
                    logging.warning(f"Sheets fetch failed, using cached special_rules. Error: {e}")
                else:
                    raise RuntimeError(f"No cached special_rules available and Sheets API failed: {e}") from e
    return _cached_special_rules
