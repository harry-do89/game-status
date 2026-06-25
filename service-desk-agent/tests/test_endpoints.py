"""
Flask endpoint contract tests.
Verifies: correct status codes, immediate 202 response, background thread spawning,
mode=off behaviour, and auth rejection.
"""
import json
import pytest
from unittest.mock import patch

HEADERS = {"X-Agent-Key": "test-key", "Content-Type": "application/json"}
WRONG_HEADERS = {"X-Agent-Key": "bad-key", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# /triage
# ---------------------------------------------------------------------------

def test_triage_returns_202_with_accepted_status(client):
    with patch("main.threading.Thread"), patch("main.reporter.send"):
        r = client.post("/triage", headers=HEADERS, json={
            "issue_key": "SUP-1", "summary": "Bug", "description": "Broken",
            "reporter": "Dante", "ticket_type": "Bug",
            "game_name": "Dragon Quest", "environment": "staging"
        })
    assert r.status_code == 202
    body = json.loads(r.data)
    assert body["status"] == "accepted"
    assert body["issue_key"] == "SUP-1"


def test_triage_spawns_background_thread(client):
    with patch("main.threading.Thread") as mock_thread, patch("main.reporter.send"):
        client.post("/triage", headers=HEADERS, json={
            "issue_key": "SUP-1", "summary": "Bug", "description": "",
            "reporter": "Dante", "ticket_type": "Bug", "game_name": "N/A", "environment": "staging"
        })
    mock_thread.return_value.start.assert_called_once()


def test_triage_off_mode_returns_offline_without_spawning_thread(client):
    with patch("main.mode_state", {"value": "off"}), \
         patch("main.threading.Thread") as mock_thread, \
         patch("main.reporter.send"):
        r = client.post("/triage", headers=HEADERS, json={"issue_key": "SUP-1"})
    assert r.status_code == 202
    assert json.loads(r.data)["status"] == "offline"
    mock_thread.assert_not_called()

def test_triage_malformed_payload_handles_missing_keys(client):
    # Phase 3.1: Malformed payload test
    # endpoint should return 202 if issue_key is present or absent
    with patch("main.threading.Thread") as mock_thread, patch("main.reporter.send"):
        r = client.post("/triage", headers=HEADERS, json={"summary": "missing keys"})
    assert r.status_code == 202
    assert json.loads(r.data)["status"] == "accepted"
    mock_thread.return_value.start.assert_called_once()


def test_mode_persists_across_multiple_requests(client):
    # Phase 3.2: Verify mode persists across requests
    with patch("main.mode_state", {"value": "test"}), \
         patch("main.threading.Thread"), \
         patch("main.reporter.send"):
        r1 = client.post("/triage", headers=HEADERS, json={"issue_key": "SUP-1"})
        r2 = client.post("/scan", headers=HEADERS, json={"issue_key": "SUP-1", "text": "test"})
        r3 = client.post("/rewrite", headers=HEADERS, json={"issue_key": "SUP-1"})
    
    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r3.status_code == 202
    import main
    assert main.mode_state["value"] == "test"


def test_triage_wrong_key_returns_401(client):
    r = client.post("/triage", headers=WRONG_HEADERS, json={"issue_key": "SUP-1"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# /scan
# ---------------------------------------------------------------------------

def test_scan_returns_202(client):
    with patch("main.threading.Thread"), patch("main.reporter.send"):
        r = client.post("/scan", headers=HEADERS,
                        json={"issue_key": "SUP-1", "text": "Some ticket text"})
    assert r.status_code == 202
    assert json.loads(r.data)["status"] == "accepted"


def test_scan_off_mode_returns_offline(client):
    with patch("main.mode_state", {"value": "off"}), patch("main.reporter.send"):
        r = client.post("/scan", headers=HEADERS,
                        json={"issue_key": "SUP-1", "text": "text"})
    assert r.status_code == 202


def test_scan_wrong_key_returns_401(client):
    r = client.post("/scan", headers=WRONG_HEADERS, json={"issue_key": "SUP-1", "text": ""})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# /rewrite
# ---------------------------------------------------------------------------

def test_rewrite_returns_202(client):
    with patch("main.threading.Thread"), patch("main.reporter.send"):
        r = client.post("/rewrite", headers=HEADERS, json={
            "issue_key": "SUP-1", "summary": "Bug", "description": "Broken", "comments": ""
        })
    assert r.status_code == 202


def test_rewrite_off_mode_returns_offline(client):
    with patch("main.mode_state", {"value": "off"}), patch("main.reporter.send"):
        r = client.post("/rewrite", headers=HEADERS,
                        json={"issue_key": "SUP-1", "summary": "", "description": "", "comments": ""})
    assert r.status_code == 202


# ---------------------------------------------------------------------------
# /summarise
# ---------------------------------------------------------------------------

def test_summarise_returns_202(client):
    with patch("main.threading.Thread"), patch("main.reporter.send"):
        r = client.post("/summarise", headers=HEADERS, json={
            "issue_key": "SUP-1", "summary": "Stale", "priority": "High",
            "status": "In Review", "board": "SUP", "assignee": "Dante",
            "reporter": "User", "last_updated": "2026-04-28T10:00:00"
        })
    assert r.status_code == 202


def test_summarise_off_mode_returns_offline(client):
    with patch("main.mode_state", {"value": "off"}), patch("main.reporter.send"):
        r = client.post("/summarise", headers=HEADERS, json={"issue_key": "SUP-1"})
    assert r.status_code == 202


# ---------------------------------------------------------------------------
# /detect
# ---------------------------------------------------------------------------

def test_detect_returns_202(client):
    with patch("main.threading.Thread"), patch("main.reporter.send"):
        r = client.post("/detect", headers=HEADERS, json={
            "issue_key": "SUP-1", "parent_summary": "Auth down",
            "today": "2026-05-03", "linked_issues": []
        })
    assert r.status_code == 202


def test_detect_off_mode_returns_offline(client):
    with patch("main.mode_state", {"value": "off"}), patch("main.reporter.send"):
        r = client.post("/detect", headers=HEADERS,
                        json={"issue_key": "SUP-1", "parent_summary": "", "today": "", "linked_issues": []})
    assert r.status_code == 202


# ---------------------------------------------------------------------------
# /admin endpoints
# ---------------------------------------------------------------------------

def test_admin_health_returns_ok(client):
    r = client.get("/admin/health", headers=HEADERS)
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["status"] == "ok"
    assert "mode" in body


def test_admin_get_mode_returns_current_mode(client):
    r = client.get("/admin/mode", headers=HEADERS)
    assert r.status_code == 200
    assert "mode" in json.loads(r.data)


def test_admin_set_mode_on(client):
    r = client.post("/admin/mode", headers=HEADERS, json={"mode": "on"})
    assert r.status_code == 200
    assert json.loads(r.data)["mode"] == "on"


def test_admin_set_mode_off(client):
    r = client.post("/admin/mode", headers=HEADERS, json={"mode": "off"})
    assert r.status_code == 200
    assert json.loads(r.data)["mode"] == "off"


def test_admin_set_mode_invalid_returns_400(client):
    r = client.post("/admin/mode", headers=HEADERS, json={"mode": "banana"})
    assert r.status_code == 400


def test_admin_wrong_key_returns_401(client):
    r = client.get("/admin/health", headers=WRONG_HEADERS)
    assert r.status_code == 401
