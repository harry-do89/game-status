"""
Unit tests for jira.py.
All HTTP calls are mocked — no real Jira connection is made.
The JiraV3Client singleton is reset before each test via autouse fixture.
"""
import pytest
from unittest.mock import patch, MagicMock, call


@pytest.fixture(autouse=True)
def reset_jira_singleton():
    import jira
    jira.JiraV3Client._instance = None
    yield
    jira.JiraV3Client._instance = None


def _response(status_code, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    r.json.return_value = {}
    return r


# ---------------------------------------------------------------------------
# update_issue()
# ---------------------------------------------------------------------------

def test_update_issue_returns_true_on_204():
    import jira
    with patch("jira.requests.Session") as mock_sess:
        mock_sess.return_value.put.return_value = _response(204)
        assert jira.update_issue("SUP-1", {"priority": {"name": "High"}}) is True


def test_update_issue_returns_false_on_4xx():
    import jira
    with patch("jira.requests.Session") as mock_sess:
        mock_sess.return_value.put.return_value = _response(400, "Bad Request")
        assert jira.update_issue("SUP-1", {"priority": {"name": "High"}}) is False


def test_update_issue_returns_false_on_connection_error():
    import jira
    with patch("jira.requests.Session") as mock_sess:
        mock_sess.return_value.put.side_effect = Exception("Connection refused")
        assert jira.update_issue("SUP-1", {}) is False


def test_update_issue_sends_fields_wrapped_in_fields_key():
    import jira
    with patch("jira.requests.Session") as mock_sess:
        mock_sess.return_value.put.return_value = _response(204)
        jira.update_issue("SUP-1", {"priority": {"name": "Critical"}})
        payload = mock_sess.return_value.put.call_args[1]["json"]
        assert "fields" in payload
        assert payload["fields"]["priority"]["name"] == "Critical"


# ---------------------------------------------------------------------------
# add_comment()
# ---------------------------------------------------------------------------

def test_add_comment_internal_uses_servicedeskapi():
    import jira
    with patch("jira.requests.Session") as mock_sess:
        mock_sess.return_value.post.return_value = _response(201)
        jira.add_comment("SUP-1", "Note", internal=True)
        url = mock_sess.return_value.post.call_args[0][0]
        assert "servicedeskapi" in url


def test_add_comment_internal_sets_public_false():
    import jira
    with patch("jira.requests.Session") as mock_sess:
        mock_sess.return_value.post.return_value = _response(201)
        jira.add_comment("SUP-1", "Internal note", internal=True)
        payload = mock_sess.return_value.post.call_args[1]["json"]
        assert payload["public"] is False


def test_add_comment_public_sets_public_true():
    import jira
    with patch("jira.requests.Session") as mock_sess:
        mock_sess.return_value.post.return_value = _response(201)
        jira.add_comment("SUP-1", "Public note", internal=False)
        payload = mock_sess.return_value.post.call_args[1]["json"]
        assert payload["public"] is True


def test_add_comment_returns_true_on_201():
    import jira
    with patch("jira.requests.Session") as mock_sess:
        mock_sess.return_value.post.return_value = _response(201)
        assert jira.add_comment("SUP-1", "Note") is True


def test_add_comment_falls_back_to_platform_v2_on_jsm_failure():
    import jira
    with patch("jira.requests.Session") as mock_sess:
        # First call (JSM API) → 403, second call (fallback v2) → 201
        mock_sess.return_value.post.side_effect = [_response(403), _response(201)]
        result = jira.add_comment("SUP-1", "Note", internal=True)
        assert result is True
        assert mock_sess.return_value.post.call_count == 2


def test_add_comment_fallback_uses_api_v2_url():
    import jira
    with patch("jira.requests.Session") as mock_sess:
        mock_sess.return_value.post.side_effect = [_response(403), _response(201)]
        jira.add_comment("SUP-1", "Note", internal=True)
        fallback_url = mock_sess.return_value.post.call_args_list[1][0][0]
        assert "/2/issue/" in fallback_url


def test_add_comment_returns_false_on_exception():
    import jira
    with patch("jira.requests.Session") as mock_sess:
        mock_sess.return_value.post.side_effect = Exception("Timeout")
        # Both primary and fallback fail
        with patch("jira._add_comment_fallback", return_value=False):
            result = jira.add_comment("SUP-1", "Note")
    assert result is False


# ---------------------------------------------------------------------------
# trigger_automation()
# ---------------------------------------------------------------------------

def test_trigger_automation_returns_true_on_202():
    import jira
    with patch("jira.requests.post") as mock_post:
        mock_post.return_value = _response(202)
        assert jira.trigger_automation("https://webhook.url", ["SUP-1"]) is True


def test_trigger_automation_accepts_all_2xx_codes():
    import jira
    for code in [200, 201, 202, 204]:
        with patch("jira.requests.post") as mock_post:
            mock_post.return_value = _response(code)
            assert jira.trigger_automation("https://webhook.url", ["SUP-1"]) is True


def test_trigger_automation_returns_false_on_no_url():
    import jira
    assert jira.trigger_automation(None, ["SUP-1"]) is False
    assert jira.trigger_automation("", ["SUP-1"]) is False


def test_trigger_automation_returns_false_on_5xx():
    import jira
    with patch("jira.requests.post") as mock_post:
        mock_post.return_value = _response(500, "Server Error")
        assert jira.trigger_automation("https://webhook.url", ["SUP-1"]) is False


def test_trigger_automation_returns_false_on_connection_error():
    import jira
    with patch("jira.requests.post") as mock_post:
        mock_post.side_effect = Exception("Connection refused")
        assert jira.trigger_automation("https://webhook.url", ["SUP-1"]) is False


def test_trigger_automation_sends_issues_list():
    import jira
    with patch("jira.requests.post") as mock_post:
        mock_post.return_value = _response(202)
        jira.trigger_automation("https://webhook.url", ["SUP-1", "SUP-2"])
        payload = mock_post.call_args[1]["json"]
        assert payload["issues"] == ["SUP-1", "SUP-2"]
