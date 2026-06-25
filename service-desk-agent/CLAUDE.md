# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

PACT Triage Agent — a Flask-based AI service desk agent that connects Jira Service Management (JSM) to Vertex AI (Gemini). Jira Automation fires webhooks to the agent; the agent classifies tickets, rewrites descriptions, flags sensitive content, nudges stale tickets, and reminds developers of blocked linked issues.

## Running the server

All scripts live in `scripts/`. Run from the `scripts/` directory:

```bash
cd scripts
source venv/bin/activate
python main.py         # starts Flask on port 8080
```

For Phase 2–3 testing with Jira Automation, run ngrok in a second terminal:

```bash
ngrok http 8080
```

## Testing

Run from the project root (not `scripts/`):

```bash
pytest                        # all tests
pytest tests/test_utils.py    # single file
pytest -k "test_triage_mode"  # single test by name
```

`conftest.py` stubs the `gemini` module entirely (no GCP init needed), mocks `pic_config` loading for all tests except `test_pic_config.py`, and auto-resets `mode_state` and `reporter.failure_counts` between every test.

## Key commands

```bash
# Health check
curl http://localhost:8080/admin/health -H "X-Agent-Key: your-key"

# Check / change agent mode (without restarting)
curl http://localhost:8080/admin/mode -H "X-Agent-Key: your-key"
curl -X POST http://localhost:8080/admin/mode \
  -H "X-Agent-Key: your-key" -H "Content-Type: application/json" \
  -d '{"mode": "test"}'   # or "on" / "off"

# Manually re-trigger triage for a ticket missed during downtime
curl -X POST http://localhost:8080/admin/triage \
  -H "X-Agent-Key: your-key" -H "Content-Type: application/json" \
  -d '{"issue_key": "SUP-123"}'

# Test an endpoint locally
curl -X POST http://localhost:8080/triage \
  -H "Content-Type: application/json" \
  -H "X-Agent-Key: your-key" \
  -d '{"issue_key":"PROJ-1","summary":"Cannot login","description":"403 since this morning","reporter":"Dante","ticket_type":"Access","game_name":"N/A","environment":"prod"}'

# Deploy to Cloud Run (Phase 4)
gcloud run deploy jira-agent --source . --region asia-southeast1
gcloud run services logs read jira-agent --region asia-southeast1 --tail=50
```

## Architecture

```
Jira Automation → (ngrok / Cloud Run) → Flask (main.py)
                                              │
                                    ┌─────────┴──────────┐
                              gemini.py              jira.py
                          (Vertex AI Gemini)     (REST write-back)
                                    │
                              gchat.py / reporter.py
                          (business notifications / audit trail)
```

### The async pattern (mandatory — do not remove)

Jira Automation has a hard 5-second timeout. Every endpoint returns `HTTP 202` immediately, then spawns a `threading.Thread` to call Gemini and write back to Jira. This means Jira Automation rules must be a single "Send web request" action — the agent handles all write-backs directly via `jira.py`.

### Agent modes

| Mode | Gemini | Jira writes | Chat notifications |
|------|--------|-------------|-------------------|
| `on` | ✅ | ✅ | ✅ |
| `test` | ✅ | ❌ | ❌ |
| `off` | ❌ | ❌ | ❌ |

Default is `test` (set via `MODE=test` in `.env`). The Agent Report space in Google Chat **always** receives a report card regardless of mode. In Phase 4 (Cloud Run), `admin.py` must be migrated to Firestore to share mode state across container instances.

### The five flows

| Endpoint | Trigger | Gemini task |
|----------|---------|-------------|
| `POST /triage` | Issue created in JSM | Classify priority, category, destination board; auto-assign PIC; trigger clone webhook |
| `POST /scan` | Issue created or comment added | Detect PII, legal threats, sensitive content |
| `POST /rewrite` | Status → Approved | Rewrite as developer task (Jira Automation does the actual clone) |
| `POST /summarise` | Scheduled every 4h | Summarise stale ticket, detect frustration |
| `POST /detect` | Linked issue status changed | Identify overdue/blocked linked items |

#### Triage destination boards

| Board | Clone webhook env var | Trigger condition |
|-------|-----------------------|-------------------|
| `PORTFOLIO` | `JIRA_WEBHOOK_PORTFOLIO` | New requests / planned work |
| `BUG_TRACKER` | `JIRA_WEBHOOK_BUG` | Bugs and production incidents |
| `DEVOPS` | `JIRA_WEBHOOK_DEVOPS` | CI/CD, provisioning, infrastructure |
| `RNG` | `JIRA_WEBHOOK_RNG_TASK` | Cheat tool access, build environments |
| `BO` | *(no clone)* | Back Office / platform config |

After triggering a clone webhook, the triage flow sleeps 5 seconds, fetches the new linked issue key, and updates the clone's assignee (or team for BUG_TRACKER).

### Module responsibilities

- `main.py` — Flask routes, background thread orchestration, mode-aware action dispatch
- `gemini.py` — Vertex AI client (`google-genai` SDK, `gemini-2.5-flash`, global endpoint)
- `jira.py` — Singleton `JiraV3Client` wrapping Jira REST API v3; uses `POST /search/jql` for searches, `servicedeskapi` for JSM internal notes
- `utils.py` — `sanitise()` (prompt injection defence), `load_prompt()` (loads `prompts/*.txt` with `{{key}}` substitution), `parse_gemini_json()` (strips markdown fences), `verify_key()` (auth)
- `admin.py` — Flask Blueprint for `/admin/mode`, `/admin/health`, and `/admin/triage`; exposes `mode_state` dict imported by `main.py`
- `pic_config.py` — Fetches PIC (Person in Charge) assignment rules from Google Sheets (`PIC_CONFIG_SHEET_ID`) with a 5-minute TTL cache; three tabs: `by_game_id` (game-specific rules), `fallback` (general/devops defaults), `special_rules` (feature flags). Falls back to cached data on Sheets API failure.
- `reporter.py` — Always-on Agent Report cards to `GCHAT_REPORT_WEBHOOK_URL`; tracks per-flow failure counts, sends `🚨 CRITICAL` alert after 3 consecutive failures
- `gchat.py` — Business notification cards to `GCHAT_WEBHOOK_URL` (suppressed in `test`/`off` mode)

### Prompts

`prompts/*.txt` files use `{{key}}` placeholders (not Python f-string `{key}`). User-supplied fields are wrapped in XML tags inside each prompt (e.g. `<description>…</description>`) to structurally separate user data from instructions — this is the second layer of prompt injection defence after `sanitise()`.

The triage prompt supports a **decline path**: if `special_rules.vnd_vietnamese_detection` is true and Vietnamese text or "VND" is detected, Gemini returns `"declined": true` with a verbatim comment to post, and the issue is transitioned to "Declined" without running any other triage steps.

## Required `.env` variables

```
AGENT_KEY=...
GCP_PROJECT=...
GOOGLE_APPLICATION_CREDENTIALS=./credentials.json
GCHAT_WEBHOOK_URL=...              # ops/dev space
GCHAT_REPORT_WEBHOOK_URL=...       # admin-only audit space
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_API_TOKEN=...
JIRA_USER_EMAIL=...
JIRA_WEBHOOK_PORTFOLIO=...         # Jira Automation webhook for PACT PORTFOLIO clone
JIRA_WEBHOOK_BUG=...               # Jira Automation webhook for BUG TRACKER clone
JIRA_WEBHOOK_DEVOPS=...            # Jira Automation webhook for DEVOPS clone
JIRA_WEBHOOK_RNG_TASK=...          # Jira Automation webhook for RNG Task clone
PIC_CONFIG_SHEET_ID=...            # Google Sheet ID for PIC assignment config
MODE=test
```

Never commit `.env` or `credentials.json`.

## Security rules (from `.agent/rules.md`)

- All user text (summary, description, comments) **must** pass through `utils.sanitise()` before being used in any prompt.
- Sanitised values **must** be wrapped in XML tags inside prompt templates.
- Every endpoint **must** catch all exceptions and call `reporter.send(..., error=str(e))` — never let a background thread crash silently.

## Jira API notes

- Use `POST /rest/api/3/search/jql` for all JQL searches (GET search is deprecated in Jira Cloud v3).
- Internal notes go via `POST /rest/servicedeskapi/request/{key}/comment` with `"public": false`; falls back to Platform API v2 on failure.
- `jira.py` is a singleton — `JiraV3Client` uses `__new__` to share one session.
