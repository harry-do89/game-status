"""
Mode behaviour tests for all 5 background process functions.
For each flow, verifies the three mode branches:
  on   — Jira/GChat writes happen
  test — writes suppressed, actions contain [MOCK] markers
  off  — suppressed (process_* is never called from the route in off mode,
         but the else branch is exercised here to guard against race conditions
         where mode changes between request receipt and thread execution)
"""
import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _json(d):
    return json.dumps(d)


TRIAGE_DATA = {
    "issue_key": "SUP-1", "summary": "Game crash", "description": "500 error",
    "reporter": "Dante", "ticket_type": "Bug", "game_name": "DragonQuest",
    "environment": "production",
}

TRIAGE_RESULT = {
    "priority": "Critical", "destination_board": "BUG_TRACKER", "category": "Bug",
    "suggested_team": "Backend", "is_production_incident": True,
    "confidence": "High", "triage_note": "Prod crash",
}

SCAN_DATA = {"issue_key": "SUP-2", "text": "Lawyers will be involved. John Smith, john@acme.com"}

SCAN_FLAGGED = {"flagged": True, "risk_level": "high", "reasons": ["legal threat", "PII"]}
SCAN_CLEAN   = {"flagged": False, "risk_level": "low",  "reasons": []}

REWRITE_DATA = {
    "issue_key": "SUP-3", "summary": "Login broken", "description": "403 since 9am", "comments": ""
}

REWRITE_RESULT = {
    "dev_summary": "Fix 403 on login endpoint",
    "dev_description": "Auth service returns 403 for all users.",
    "acceptance_criteria": ["Login succeeds", "No 403 errors"]
}

SUMMARISE_DATA = {
    "issue_key": "SUP-4", "summary": "Payment timeout", "board": "SUP",
    "priority": "High", "status": "In Review", "assignee": "dev@co.com",
    "reporter": "user@co.com", "last_updated": "2026-04-28T08:00:00",
    "last_comment": "Waiting on vendor", "last_comment_author": "dev@co.com",
    "last_comment_date": "2026-04-28T08:00:00",
}

STALE_RESULT = {
    "is_stale": True, "ticket_key": "SUP-4", "priority": "High", "board": "SUP",
    "inactive_business_hours": 12, "threshold_business_hours": 8,
    "stall_reason": "waiting_for_reporter",
    "last_activity_summary": "Team asked a question with no reply.",
    "recommended_action": "Chase the reporter.",
    "urgency_label": "🟠 High Stale",
    "gchat_message": "SUP-4 has been stale for 12 hours."
}

NOT_STALE_RESULT = {
    "is_stale": False, "inactive_business_hours": 2,
    "threshold_business_hours": 8, "ticket_key": "SUP-4"
}

DETECT_DATA = {
    "issue_key": "SUP-5", "parent_summary": "Release blocker",
    "today": "2026-05-04",
    "linked_issues": [{"key": "DEV-101", "status": "Overdue", "due": "2026-04-30"}]
}

DETECT_ACTION = {"action_needed": True, "blocked_issues": ["DEV-101"],
                 "reminder_message": "DEV-101 is overdue."}
DETECT_NO_ACTION = {"action_needed": False, "blocked_issues": [], "reminder_message": ""}


# ---------------------------------------------------------------------------
# process_triage — suppressed (else branch)
# ---------------------------------------------------------------------------

class TestProcessTriageSuppressed:
    def test_suppressed_mode_does_not_call_jira(self, app):
        from main import process_triage
        with patch("main.mode_state", {"value": "off"}), \
             patch("main.gemini.ask", return_value=_json(TRIAGE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.update_issue") as mock_update, \
             patch("main.jira.add_comment") as mock_comment, \
             patch("main.reporter.send"):
            process_triage(TRIAGE_DATA)
        mock_update.assert_not_called()
        mock_comment.assert_not_called()

    def test_suppressed_mode_reporter_receives_suppressed_action(self, app):
        from main import process_triage
        with patch("main.mode_state", {"value": "off"}), \
             patch("main.gemini.ask", return_value=_json(TRIAGE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.reporter.send") as mock_report:
            process_triage(TRIAGE_DATA)
        _, _, _, _, _, actions, _ = mock_report.call_args[0]
        assert any("suppressed" in a for a in actions)


# ---------------------------------------------------------------------------
# process_scan
# ---------------------------------------------------------------------------

class TestProcessScan:
    def _run(self, mode, gemini_result, **extra_patches):
        from main import process_scan
        patches = {
            "main.mode_state": {"value": mode},
            "main.gemini.ask": MagicMock(return_value=_json(gemini_result)),
            "main.utils.load_prompt": MagicMock(return_value="prompt"),
            "main.reporter.send": MagicMock(),
            **extra_patches
        }
        with patch("main.jira.add_comment") as mock_comment, \
             patch("main.gchat.send_card") as mock_chat, \
             patch.dict("main.__dict__", {}):

            context_patches = [patch(k, v) for k, v in patches.items()]
            for p in context_patches:
                p.start()
            try:
                process_scan(SCAN_DATA)
            finally:
                for p in context_patches:
                    p.stop()

            return mock_comment, mock_chat, patches["main.reporter.send"]

    def test_on_mode_flagged_adds_internal_comment(self, app):
        from main import process_scan
        with patch("main.mode_state", {"value": "on"}), \
             patch("main.gemini.ask", return_value=_json(SCAN_FLAGGED)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment", return_value=True) as mock_comment, \
             patch("main.gchat.send_card") as mock_chat, \
             patch("main.reporter.send"):
            process_scan(SCAN_DATA)
        mock_comment.assert_called_once()
        _, comment_body = mock_comment.call_args[0]
        internal = mock_comment.call_args[1].get("internal", False)
        assert internal is True
        assert "Sensitive content" in comment_body

    def test_on_mode_flagged_sends_gchat_alert(self, app):
        from main import process_scan
        with patch("main.mode_state", {"value": "on"}), \
             patch("main.gemini.ask", return_value=_json(SCAN_FLAGGED)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment", return_value=True), \
             patch("main.gchat.send_card") as mock_chat, \
             patch("main.reporter.send"):
            process_scan(SCAN_DATA)
        mock_chat.assert_called_once()

    def test_on_mode_not_flagged_skips_jira_and_gchat(self, app):
        from main import process_scan
        with patch("main.mode_state", {"value": "on"}), \
             patch("main.gemini.ask", return_value=_json(SCAN_CLEAN)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment") as mock_comment, \
             patch("main.gchat.send_card") as mock_chat, \
             patch("main.reporter.send"):
            process_scan(SCAN_DATA)
        mock_comment.assert_not_called()
        mock_chat.assert_not_called()

    def test_test_mode_flagged_does_not_call_jira(self, app):
        from main import process_scan
        with patch("main.gemini.ask", return_value=_json(SCAN_FLAGGED)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment") as mock_comment, \
             patch("main.gchat.send_card") as mock_chat, \
             patch("main.reporter.send"):
            process_scan(SCAN_DATA)  # default mode=test from conftest
        mock_comment.assert_not_called()
        mock_chat.assert_not_called()

    def test_test_mode_flagged_reporter_has_mock_actions(self, app):
        from main import process_scan
        with patch("main.gemini.ask", return_value=_json(SCAN_FLAGGED)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.reporter.send") as mock_report:
            process_scan(SCAN_DATA)
        _, _, _, _, _, actions, _ = mock_report.call_args[0]
        assert any("[MOCK]" in a for a in actions)

    def test_test_mode_not_flagged_reporter_shows_suppressed(self, app):
        from main import process_scan
        with patch("main.gemini.ask", return_value=_json(SCAN_CLEAN)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.reporter.send") as mock_report:
            process_scan(SCAN_DATA)
        _, _, _, _, _, actions, _ = mock_report.call_args[0]
        assert any("suppressed" in a or "not flagged" in a for a in actions)


# ---------------------------------------------------------------------------
# process_rewrite
# ---------------------------------------------------------------------------

class TestProcessRewrite:
    def test_on_mode_posts_internal_comment(self, app):
        from main import process_rewrite
        with patch("main.mode_state", {"value": "on"}), \
             patch("main.gemini.ask", return_value=_json(REWRITE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment", return_value=True) as mock_comment, \
             patch("main.reporter.send"):
            process_rewrite(REWRITE_DATA)
        mock_comment.assert_called_once()
        _, comment_body = mock_comment.call_args[0]
        internal = mock_comment.call_args[1].get("internal", False)
        assert internal is True
        assert "Technical Rewrite" in comment_body
        assert "Fix 403" in comment_body

    def test_on_mode_comment_includes_acceptance_criteria(self, app):
        from main import process_rewrite
        with patch("main.mode_state", {"value": "on"}), \
             patch("main.gemini.ask", return_value=_json(REWRITE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment", return_value=True) as mock_comment, \
             patch("main.reporter.send"):
            process_rewrite(REWRITE_DATA)
        _, comment_body = mock_comment.call_args[0]
        assert "Login succeeds" in comment_body

    def test_test_mode_does_not_call_jira(self, app):
        from main import process_rewrite
        with patch("main.gemini.ask", return_value=_json(REWRITE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment") as mock_comment, \
             patch("main.reporter.send"):
            process_rewrite(REWRITE_DATA)
        mock_comment.assert_not_called()

    def test_test_mode_reporter_has_mock_action(self, app):
        from main import process_rewrite
        with patch("main.gemini.ask", return_value=_json(REWRITE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.reporter.send") as mock_report:
            process_rewrite(REWRITE_DATA)
        _, _, _, _, _, actions, _ = mock_report.call_args[0]
        assert any("[MOCK]" in a for a in actions)

    def test_suppressed_mode_does_not_call_jira(self, app):
        from main import process_rewrite
        with patch("main.mode_state", {"value": "off"}), \
             patch("main.gemini.ask", return_value=_json(REWRITE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment") as mock_comment, \
             patch("main.reporter.send"):
            process_rewrite(REWRITE_DATA)
        mock_comment.assert_not_called()

    def test_reporter_always_called(self, app):
        from main import process_rewrite
        for mode in ("on", "test", "off"):
            with patch("main.mode_state", {"value": mode}), \
                 patch("main.gemini.ask", return_value=_json(REWRITE_RESULT)), \
                 patch("main.utils.load_prompt", return_value="prompt"), \
                 patch("main.jira.add_comment", return_value=True), \
                 patch("main.reporter.send") as mock_report:
                process_rewrite(REWRITE_DATA)
            mock_report.assert_called_once()


# ---------------------------------------------------------------------------
# process_summarise
# ---------------------------------------------------------------------------

class TestProcessSummarise:
    def test_on_mode_stale_adds_nudge_comment(self, app):
        from main import process_summarise
        with patch("main.mode_state", {"value": "on"}), \
             patch("main.gemini.ask", return_value=_json(STALE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment", return_value=True) as mock_comment, \
             patch("main.gchat.send_card"), \
             patch("main.reporter.send"):
            process_summarise(SUMMARISE_DATA)
        mock_comment.assert_called_once()
        issue_key_arg, comment_body = mock_comment.call_args[0]
        assert "Stale Ticket Nudge" in comment_body

    def test_on_mode_stale_sends_gchat_card(self, app):
        from main import process_summarise
        with patch("main.mode_state", {"value": "on"}), \
             patch("main.gemini.ask", return_value=_json(STALE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment", return_value=True), \
             patch("main.gchat.send_card") as mock_chat, \
             patch("main.reporter.send"):
            process_summarise(SUMMARISE_DATA)
        mock_chat.assert_called_once()
        assert "Stale" in mock_chat.call_args[1]["title"]

    def test_on_mode_not_stale_skips_jira_and_gchat(self, app):
        from main import process_summarise
        with patch("main.mode_state", {"value": "on"}), \
             patch("main.gemini.ask", return_value=_json(NOT_STALE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment") as mock_comment, \
             patch("main.gchat.send_card") as mock_chat, \
             patch("main.reporter.send") as mock_report:
            process_summarise(SUMMARISE_DATA)
        mock_comment.assert_not_called()
        mock_chat.assert_not_called()
        _, _, _, _, _, actions, _ = mock_report.call_args[0]
        assert any("not stale" in a.lower() for a in actions)

    def test_test_mode_stale_does_not_call_jira(self, app):
        from main import process_summarise
        with patch("main.gemini.ask", return_value=_json(STALE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment") as mock_comment, \
             patch("main.gchat.send_card") as mock_chat, \
             patch("main.reporter.send"):
            process_summarise(SUMMARISE_DATA)
        mock_comment.assert_not_called()
        mock_chat.assert_not_called()

    def test_test_mode_stale_reporter_has_mock_actions(self, app):
        from main import process_summarise
        with patch("main.gemini.ask", return_value=_json(STALE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.reporter.send") as mock_report:
            process_summarise(SUMMARISE_DATA)
        _, _, _, _, _, actions, _ = mock_report.call_args[0]
        assert any("[MOCK]" in a for a in actions)

    def test_test_mode_not_stale_reports_no_action(self, app):
        from main import process_summarise
        with patch("main.gemini.ask", return_value=_json(NOT_STALE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.reporter.send") as mock_report:
            process_summarise(SUMMARISE_DATA)
        _, _, _, _, _, actions, _ = mock_report.call_args[0]
        assert any("not stale" in a.lower() for a in actions)

    def test_suppressed_mode_does_not_call_jira_or_gchat(self, app):
        from main import process_summarise
        with patch("main.mode_state", {"value": "off"}), \
             patch("main.gemini.ask", return_value=_json(STALE_RESULT)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment") as mock_comment, \
             patch("main.gchat.send_card") as mock_chat, \
             patch("main.reporter.send"):
            process_summarise(SUMMARISE_DATA)
        mock_comment.assert_not_called()
        mock_chat.assert_not_called()


# ---------------------------------------------------------------------------
# process_detect
# ---------------------------------------------------------------------------

class TestProcessDetect:
    def test_on_mode_action_needed_adds_reminder_comment(self, app):
        from main import process_detect
        with patch("main.mode_state", {"value": "on"}), \
             patch("main.gemini.ask", return_value=_json(DETECT_ACTION)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment", return_value=True) as mock_comment, \
             patch("main.gchat.send_card"), \
             patch("main.reporter.send"):
            process_detect(DETECT_DATA)
        mock_comment.assert_called_once()
        issue_key_arg, comment_body = mock_comment.call_args[0]
        assert "Linked Issue Reminder" in comment_body

    def test_on_mode_action_needed_sends_gchat_alert(self, app):
        from main import process_detect
        with patch("main.mode_state", {"value": "on"}), \
             patch("main.gemini.ask", return_value=_json(DETECT_ACTION)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment", return_value=True), \
             patch("main.gchat.send_card") as mock_chat, \
             patch("main.reporter.send"):
            process_detect(DETECT_DATA)
        mock_chat.assert_called_once()
        assert "DEV-101" in str(mock_chat.call_args)

    def test_on_mode_no_action_skips_jira_and_gchat(self, app):
        from main import process_detect
        with patch("main.mode_state", {"value": "on"}), \
             patch("main.gemini.ask", return_value=_json(DETECT_NO_ACTION)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment") as mock_comment, \
             patch("main.gchat.send_card") as mock_chat, \
             patch("main.reporter.send"):
            process_detect(DETECT_DATA)
        mock_comment.assert_not_called()
        mock_chat.assert_not_called()

    def test_test_mode_does_not_call_jira_or_gchat(self, app):
        from main import process_detect
        with patch("main.gemini.ask", return_value=_json(DETECT_ACTION)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment") as mock_comment, \
             patch("main.gchat.send_card") as mock_chat, \
             patch("main.reporter.send"):
            process_detect(DETECT_DATA)
        mock_comment.assert_not_called()
        mock_chat.assert_not_called()

    def test_suppressed_mode_does_not_call_jira_or_gchat(self, app):
        from main import process_detect
        with patch("main.mode_state", {"value": "off"}), \
             patch("main.gemini.ask", return_value=_json(DETECT_ACTION)), \
             patch("main.utils.load_prompt", return_value="prompt"), \
             patch("main.jira.add_comment") as mock_comment, \
             patch("main.gchat.send_card") as mock_chat, \
             patch("main.reporter.send"):
            process_detect(DETECT_DATA)
        mock_comment.assert_not_called()
        mock_chat.assert_not_called()

    def test_reporter_always_called_regardless_of_mode(self, app):
        from main import process_detect
        for mode in ("on", "test", "off"):
            with patch("main.mode_state", {"value": mode}), \
                 patch("main.gemini.ask", return_value=_json(DETECT_NO_ACTION)), \
                 patch("main.utils.load_prompt", return_value="prompt"), \
                 patch("main.jira.add_comment", return_value=True), \
                 patch("main.reporter.send") as mock_report:
                process_detect(DETECT_DATA)
            mock_report.assert_called_once()
