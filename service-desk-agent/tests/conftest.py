import os
import sys
from unittest.mock import MagicMock

# Set environment variables before any project imports
os.environ.setdefault("AGENT_KEY", "test-key")
os.environ.setdefault("GCP_PROJECT", "test-project")
os.environ.setdefault("JIRA_BASE_URL", "https://test.atlassian.net")
os.environ.setdefault("JIRA_API_TOKEN", "test-token")
os.environ.setdefault("JIRA_USER_EMAIL", "test@test.com")
os.environ.setdefault("GCHAT_WEBHOOK_URL", "https://chat.googleapis.com/v1/spaces/test")
os.environ.setdefault("GCHAT_REPORT_WEBHOOK_URL", "https://chat.googleapis.com/v1/spaces/report")
os.environ.setdefault("MODE", "test")
os.environ.setdefault("JIRA_WEBHOOK_PORTFOLIO", "https://jira.webhook/portfolio")
os.environ.setdefault("JIRA_WEBHOOK_BUG", "https://jira.webhook/bug")
os.environ.setdefault("JIRA_WEBHOOK_DEVOPS", "https://jira.webhook/devops")
os.environ.setdefault("JIRA_WEBHOOK_RNG_TASK", "https://jira.webhook/rng-task")

# Stub the gemini module so main.py never tries to initialise a GCP client
sys.modules["gemini"] = MagicMock()

# Make scripts/ importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import pytest


@pytest.fixture(scope="session")
def app():
    import main
    main.app.config["TESTING"] = True
    return main.app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def reset_mode():
    """Reset agent mode to 'test' before and after every test."""
    import admin
    admin.mode_state["value"] = "test"
    yield
    admin.mode_state["value"] = "test"


@pytest.fixture(autouse=True)
def reset_reporter_failures():
    """Reset per-flow failure counters before every test."""
    import reporter
    reporter.failure_counts.clear()
    yield
    reporter.failure_counts.clear()


@pytest.fixture(autouse=True)
def mock_pic_config(request, monkeypatch):
    """Mock Google Sheets config loading to avoid hitting API or throwing errors in tests."""
    if "test_pic_config" in request.node.nodeid:
        return
    import pic_config
    monkeypatch.setattr(pic_config, "load_pic_config", lambda *a, **kw: {
        "by_game_id": {},
        "fallback": {
            "general": {"pic_name": "Fallback PIC", "email": "fallback@test.com", "account_id": "acc-general"},
            "devops": {"pic_name": "DevOps PIC", "email": "devops-fallback@test.com", "account_id": "acc-devops"}
        }
    })
    monkeypatch.setattr(pic_config, "load_special_rules", lambda *a, **kw: {
        "vnd_vietnamese_detection": True
    })

