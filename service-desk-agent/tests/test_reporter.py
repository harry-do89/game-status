"""
Unit tests for reporter.py.
Covers: failure counting, critical alert threshold, count reset, and send() behaviour.
"""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Failure counting and critical alert
# ---------------------------------------------------------------------------

def test_record_failure_increments_count():
    import reporter
    reporter.record_failure("triage")
    assert reporter.failure_counts["triage"] == 1


def test_record_failure_tracks_per_flow_independently():
    import reporter
    reporter.record_failure("triage")
    reporter.record_failure("scan")
    reporter.record_failure("triage")
    assert reporter.failure_counts["triage"] == 2
    assert reporter.failure_counts["scan"] == 1


def test_critical_alert_fires_exactly_at_threshold_of_3():
    import reporter
    with patch("reporter.send_critical_alert") as mock_alert:
        reporter.record_failure("triage")
        reporter.record_failure("triage")
        mock_alert.assert_not_called()
        reporter.record_failure("triage")
        mock_alert.assert_called_once_with("triage", 3)


def test_failure_count_resets_to_zero_after_critical_alert():
    import reporter
    with patch("reporter.send_critical_alert"):
        reporter.record_failure("triage")
        reporter.record_failure("triage")
        reporter.record_failure("triage")
    assert reporter.failure_counts["triage"] == 0


def test_second_batch_of_failures_triggers_new_alert():
    import reporter
    with patch("reporter.send_critical_alert") as mock_alert:
        for _ in range(6):  # two full cycles
            reporter.record_failure("triage")
    assert mock_alert.call_count == 2


# ---------------------------------------------------------------------------
# send() — always posts to the report webhook
# ---------------------------------------------------------------------------

def test_send_posts_to_gchat_report_webhook():
    import reporter, os
    with patch("reporter.requests.post") as mock_post:
        reporter.send("triage", "on", "SUP-1", "Summary", {"priority": "High"}, ["Jira updated"], 1200)
        mock_post.assert_called_once()
        called_url = mock_post.call_args[0][0]
        assert called_url == os.getenv("GCHAT_REPORT_WEBHOOK_URL")


def test_send_with_error_calls_record_failure():
    import reporter
    with patch("reporter.requests.post"), \
         patch("reporter.record_failure") as mock_record:
        reporter.send("triage", "on", "SUP-1", "Summary", {}, [], 500, error="Gemini timeout")
    mock_record.assert_called_once_with("triage")


def test_send_without_error_does_not_call_record_failure():
    import reporter
    with patch("reporter.requests.post"), \
         patch("reporter.record_failure") as mock_record:
        reporter.send("triage", "on", "SUP-1", "Summary", {"priority": "High"}, ["Done"], 1200)
    mock_record.assert_not_called()


def test_send_fires_in_all_modes():
    import reporter
    with patch("reporter.requests.post") as mock_post:
        for mode in ("on", "test", "off"):
            mock_post.reset_mock()
            reporter.send("triage", mode, "SUP-1", "Summary", {}, [], 0)
            mock_post.assert_called_once()


def test_send_card_header_contains_flow_and_mode():
    import reporter
    with patch("reporter.requests.post") as mock_post:
        reporter.send("triage", "on", "SUP-1", "Summary", {}, ["Done"], 800)
        payload = mock_post.call_args[1]["json"]
        subtitle = payload["cardsV2"][0]["card"]["header"]["subtitle"]
        assert "triage" in subtitle.lower()
        assert "ON" in subtitle


def test_send_no_crash_when_webhook_url_missing(monkeypatch):
    import reporter
    monkeypatch.setenv("GCHAT_REPORT_WEBHOOK_URL", "")
    reporter.send("triage", "on", "SUP-1", "Summary", {}, [], 0)  # must not raise
