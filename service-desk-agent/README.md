# PACT Triage Agent

A Flask-based AI service desk agent that connects Jira Service Management (JSM) to Google Vertex AI (Gemini 2.5 Flash). Jira Automation fires webhooks to the agent; the agent classifies tickets, routes them to the correct board, auto-assigns a PIC (Person in Charge), posts internal notes, detects sensitive content, nudges stale tickets, and reminds developers of blocked linked issues.

---

## Architecture

```
Jira Automation → (ngrok / Cloud Run URL) → Flask (main.py)
                                                    │
                                       ┌────────────┴────────────┐
                                  gemini.py                  jira.py
                             (Vertex AI Gemini)          (REST write-back)
                                       │
                               gchat.py / reporter.py
                          (business notifications / audit trail)
                                       │
                               pic_config.py
                          (Google Sheets PIC assignment)
```

Every endpoint returns HTTP 202 immediately and spawns a background thread. Jira Automation has a hard 5-second timeout — this pattern is mandatory.

### Dashboards & Sibling Repositories
The Flask application also dynamically mounts two analysis dashboard blueprints at startup if their sibling directories are present:
- **SUP Analysis Dashboard** (mounted at `/sup`): Loads blueprint from `../sup-analysis/server.py`
- **Verticals Dashboard** (mounted at `/verticals`): Loads blueprint from `../pact_verticals_analysis/server.py`

For these dashboards to function, the developer must clone their corresponding sibling repositories into the same parent directory alongside `service-desk-agent`.

---

## Required Services & Setup

### 1. Google Cloud Platform (Vertex AI)

**What it does:** Hosts Gemini 2.5 Flash, which powers all AI decisions.

> [!IMPORTANT]
> **New Developer Setup:** You must create your own **new GCP Project** for this agent, enable Vertex AI, download your own service account credentials JSON, and configure `GCP_PROJECT` and `GOOGLE_APPLICATION_CREDENTIALS` in your `.env` file accordingly.

**Setup steps:**
1. Create a **new GCP project** (e.g., `jira-agent-dev`).
2. Enable the **Vertex AI API**.
3. Create a **service account** with the role **Vertex AI User**.
4. Create a `credentials/` directory in the project root (excluded from Git) and save your service account key JSON inside it.
5. Set `GCP_PROJECT` (to your new GCP project ID) and `GOOGLE_APPLICATION_CREDENTIALS` (to the path of the service account JSON key) in your local `.env`.

> The agent uses the `global` endpoint with the `google-genai` SDK (`vertexai=True`). Model: `gemini-2.5-flash`.

---

### 2. Jira Service Management (JSM)

**What it does:** Source of all tickets; the agent writes back priority, assignee, internal comments, and triggers clone webhooks via Automation rules.

#### 2a. API Token

1. Go to **Atlassian Account Settings → Security → API tokens**.
2. Create a token → set as `JIRA_API_TOKEN` in `.env`.
3. Set `JIRA_USER_EMAIL` to the account email that owns the token.
4. Set `JIRA_BASE_URL` to `https://your-domain.atlassian.net`.

#### 2b. Jira Automation Rules (one per board)

For each destination board, create a Jira Automation rule:

| Board | Trigger | Action | Env var for webhook |
|-------|---------|--------|---------------------|
| PORTFOLIO | Webhook received | Clone issue to PACT PORTFOLIO project | `JIRA_WEBHOOK_PORTFOLIO` |
| BUG_TRACKER | Webhook received | Clone issue to BUG TRACKER project | `JIRA_WEBHOOK_BUG` |
| DEVOPS | Webhook received | Clone issue to DEVOPS project | `JIRA_WEBHOOK_DEVOPS` |
| RNG | Webhook received | Clone issue to RNG TASK project | `JIRA_WEBHOOK_RNG_TASK` |

**Rule setup (each):**
1. In Jira → Project Settings → Automation → **Create rule**.
2. Trigger: **Incoming webhook** → copy the generated webhook URL → paste into the corresponding `.env` variable.
3. Action: **Clone issue** to the target project with desired field mapping.
4. The agent calls these webhooks with `{"issues": ["SUP-XXX"]}` after triage.

#### 2c. Automation Rules that call the Agent

Create one rule per flow that calls the agent's endpoint:

| Flow | Jira trigger | Agent endpoint | Required payload fields |
|------|-------------|---------------|------------------------|
| Triage | Issue created in JSM | `POST /triage` | `issue_key`, `summary`, `description`, `reporter`, `ticket_type`, `game_name`, `environment`, `game_id` |
| Scan | Issue created or comment added | `POST /scan` | `issue_key`, `text` |
| Rewrite | Status transition → Approved | `POST /rewrite` | `issue_key`, `summary`, `description`, `comments` |
| Summarise | Scheduled (every 4h) | `POST /summarise` | `issue_key`, `summary`, `board`, `priority`, `status`, `assignee`, `reporter`, `last_updated`, `last_comment`, `last_comment_author`, `last_comment_date` |
| Detect | Linked issue status changed | `POST /detect` | `issue_key`, `parent_summary`, `today`, `linked_issues` (array) |

All rules must use **"Send web request"** action with:
- URL: `{ngrok or Cloud Run base URL}/{endpoint}`
- Method: `POST`
- Headers: `X-Agent-Key: <your AGENT_KEY>`, `Content-Type: application/json`

**Webhook body templates (use Jira Smart Values — these are NOT hardcoded):**

`/triage`:
```json
{
  "issue_key": "{{issue.key}}",
  "summary": "{{issue.summary}}",
  "description": "{{issue.description}}",
  "reporter": "{{issue.reporter.displayName}}",
  "ticket_type": "{{issue.requestType.name}}",
  "game_name": "{{issue.customfield_10664}}",
  "environment": "{{issue.customfield_10718}}",
  "game_id": "{{issue.customfield_10814}}"
}
```

> `ticket_type` **must** use `{{issue.requestType.name}}` (JSM customer-facing request type, e.g. "DevOps Support", "New Feature Request") — not `{{issue.issueType.name}}` (underlying Jira type like "Task" or "Bug"). The agent's PIC routing logic and board routing depends on the request type name.

**Custom field reference (verified against this Jira instance):**

| Agent field | Jira field name | Field ID |
|-------------|----------------|----------|
| `game_id` | Game ID | `customfield_10814` |
| `game_name` | Project/Game Type | `customfield_10664` |
| `environment` | Environment affected | `customfield_10718` |

> `game_id` is the most critical field — it drives PIC assignment. If a ticket is created without a Project ID, the agent falls back to the general fallback PIC and appends a ⚠️ warning in the report card. Ensure the JSM **portal form** for relevant request types includes a required "Project ID" field so submitters cannot omit it.

`/scan` (issue created):
```json
{
  "issue_key": "{{issue.key}}",
  "text": "{{issue.summary}} {{issue.description}}"
}
```

`/scan` (comment added):
```json
{
  "issue_key": "{{issue.key}}",
  "text": "{{comment.body}}"
}
```

`/rewrite`:
```json
{
  "issue_key": "{{issue.key}}",
  "summary": "{{issue.summary}}",
  "description": "{{issue.description}}",
  "comments": "{{issue.comments.last.body}}"
}
```

`/summarise`:
```json
{
  "issue_key": "{{issue.key}}",
  "summary": "{{issue.summary}}",
  "board": "{{issue.project.key}}",
  "priority": "{{issue.priority.name}}",
  "status": "{{issue.status.name}}",
  "assignee": "{{issue.assignee.displayName}}",
  "reporter": "{{issue.reporter.displayName}}",
  "last_updated": "{{issue.updated}}",
  "last_comment": "{{issue.comments.last.body}}",
  "last_comment_author": "{{issue.comments.last.author.displayName}}",
  "last_comment_date": "{{issue.comments.last.created}}"
}
```

`/detect`:
```json
{
  "issue_key": "{{issue.key}}",
  "parent_summary": "{{issue.summary}}",
  "today": "{{now.jiraDate}}",
  "linked_issues": "{{issue.linkedIssues}}"
}
```

---

### 3. Google Sheets (PIC Assignment Config)

**What it does:** Stores PIC (Person in Charge) assignment rules. The agent reads this on each triage with a 5-minute TTL cache.

**Setup steps:**
1. Create a Google Sheet and note its ID from the URL (`/spreadsheets/d/{SHEET_ID}/`).
2. Set `PIC_CONFIG_SHEET_ID` in `.env`.
3. Share the sheet with the **service account email** (from step 1 of GCP setup) with Viewer access.
4. Create three tabs exactly as described below.

#### Tab 1: `fallback`

Columns: `A=pic_name | B=pic_email | C=pic_account_id | D=role`

| pic_name | pic_email | pic_account_id | role |
|----------|-----------|---------------|------|
| Dana (BG - Delivery Manager) | dana@company.io | 712020:xxx | general |
| DevOps Engineer | devops@company.io | 712020:yyy | devops |
| Kent Nguyen | kent@company.io | 712020:zzz | *(blank — lookup only)* |

- Rows with a `role` value are used as **fallback assignment rules**.
- All rows (with or without role) are loaded into a **lookup dict** so `by_game_id` entries can resolve `pic_name` and `pic_account_id` from `pic_email`.
- **`general`** role → catch-all fallback PIC.
- **`devops`** role → assigned when `ticket_type == "DevOps Support"`.
- `pic_account_id` is the Jira Cloud `accountId` (found via Jira user management). Required to set assignee — email alone does not work in Jira REST API v3.

#### Tab 2: `by_game_id`

Columns: `A=game_id | B=team_name | C=team_id | D=pic_email | E=active`

| game_id | team_name | team_id | pic_email | active |
|---------|-----------|---------|-----------|--------|
| 1969 | PACT RNG Fish | fabbf1c2-... | kent@company.io | TRUE |

- `game_id` must match exactly what is sent in the Jira Automation webhook payload.
- `team_id` is the Jira team UUID (used to set `customfield_10001` on BUG_TRACKER clones).
- `pic_email` resolves to `pic_name` + `pic_account_id` via the `fallback` tab lookup at load time.
- Set `active=FALSE` to disable a rule without deleting it.

#### Tab 3: `special_rules`

Columns: `A=rule_name | B=enabled`

| rule_name | enabled |
|-----------|---------|
| vnd_vietnamese_detection | TRUE |

- **`vnd_vietnamese_detection`**: when `TRUE`, Gemini checks for Vietnamese text or "VND" currency mentions. If detected, the ticket is declined and transitioned to "Declined" status without further triage.

---

### 4. Google Chat Webhooks

**What it does:** Two separate spaces receive notifications.

**Setup steps (each space):**
1. In Google Chat, open the target space → **Apps & integrations → Webhooks → Add webhook**.
2. Copy the webhook URL.

| Webhook | Purpose | Env var |
|---------|---------|---------|
| Ops/Dev space | Business-facing cards (stale tickets, sensitive content flags) — suppressed in `test`/`off` mode | `GCHAT_WEBHOOK_URL` |
| Agent Report space | Always-on audit trail showing every agent decision, mode, and action taken | `GCHAT_REPORT_WEBHOOK_URL` |

> `GCHAT_WEBHOOK_URL` can be left blank if the `summarise` flow is not yet in use. The agent logs a warning and skips silently.

---

### 5. ngrok (Local Development)

**What it does:** Exposes the local Flask server to the internet so Jira Automation can reach it.

**Setup:**
1. Install ngrok: `brew install ngrok` (or download from ngrok.com).
2. Authenticate: `ngrok config add-authtoken <your-token>`.
3. Run: `ngrok http 8080` → copy the `https://xxx.ngrok-free.app` URL.
4. Update all Jira Automation "Send web request" actions with the new ngrok URL.

> The ngrok URL changes on every restart. For stable deployments, use Cloud Run (see Phase 4).

---

## Installation

```bash
# From the project root
python3 -m venv venv
source venv/bin/activate
pip install -r scripts/requirements.txt -r requirements-dev.txt
```

Create a `credentials/` directory in the project root, and place your GCP service account JSON key inside it. By default, the code looks for `credentials/jira-agent-personal-f0bd8631745a.json` if `GOOGLE_APPLICATION_CREDENTIALS` is not set. You can customize this by setting the path in the `.env` variable `GOOGLE_APPLICATION_CREDENTIALS`.

---

## Environment Variables

Create `.env` in the project root. **Never commit this file.**

```env
# Auth
AGENT_KEY=your-secret-key-here          # Shared secret in X-Agent-Key header for all requests

# GCP / Vertex AI
GCP_PROJECT=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=./credentials/your-service-account.json

# Jira
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_API_TOKEN=your-jira-api-token
JIRA_USER_EMAIL=agent-user@company.io

# Jira Automation clone webhooks (one per board)
JIRA_WEBHOOK_PORTFOLIO=https://api-private.atlassian.com/automation/webhooks/...
JIRA_WEBHOOK_BUG=https://api-private.atlassian.com/automation/webhooks/...
JIRA_WEBHOOK_DEVOPS=https://api-private.atlassian.com/automation/webhooks/...
JIRA_WEBHOOK_RNG_TASK=https://api-private.atlassian.com/automation/webhooks/...

# Google Chat
GCHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/.../messages?key=...   # ops space
GCHAT_REPORT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/.../messages?key=...  # audit space

# Google Sheets PIC config
PIC_CONFIG_SHEET_ID=your-google-sheet-id

# Agent mode: on | test | off  (default: test)
MODE=test
```

---

## Running Locally

Open two terminals from the project root:

**Terminal 1 — Flask server:**
```bash
source venv/bin/activate
cd scripts
python main.py
```

**Terminal 2 — ngrok tunnel:**
```bash
ngrok http 8080
```

Copy the `https://xxx.ngrok-free.app` URL into all Jira Automation rules.

**Health check:**
```bash
curl http://localhost:8080/admin/health -H "X-Agent-Key: your-key"
```

---

## Agent Modes

| Mode | Gemini | Jira writes | GChat notifications | Agent Report |
|------|--------|-------------|--------------------:|:------------:|
| `on` | ✅ | ✅ | ✅ | ✅ always |
| `test` | ✅ | ❌ | ❌ | ✅ always |
| `off` | ❌ | ❌ | ❌ | ✅ always |

Default is `test`. Change without restarting:

```bash
curl -X POST http://localhost:8080/admin/mode \
  -H "X-Agent-Key: your-key" -H "Content-Type: application/json" \
  -d '{"mode": "on"}'
```

---

## The Five Flows

> [!WARNING]
> **Missing Prompt Files:**
> Currently, the files `prompts/scan.txt`, `prompts/rewrite.txt`, and `prompts/detect.txt` are not present in this repository. Running `/scan`, `/rewrite`, or `/detect` endpoints will result in a `FileNotFoundError` inside `utils.load_prompt()`.
>
> To use these endpoints, you must create these files in the `prompts/` directory. You can find detailed descriptions and generation instructions for each of these prompts in [docs/Jira_AI_Agent_Implementation_Plan_v2.md](file:///Users/kent/Projects/service-desk-agent/docs/Jira_AI_Agent_Implementation_Plan_v2.md).

### POST `/triage`
**Trigger:** Issue created in JSM.

**What it does:**
1. Loads PIC config from Google Sheets.
2. Calls Gemini to classify: `priority`, `destination_board`, `category`, `suggested_team`, `confidence`, `triage_note`.
3. Applies **Vietnamese/VND decline path** if special rule is enabled.
4. Assigns PIC based on `game_id` → `by_game_id` lookup → fallback rules (devops or general).
5. Updates Jira: sets priority + assignee by `accountId`.
6. Posts internal triage note as a JSM internal comment.
7. Triggers the clone webhook for the destination board.
8. After 5-second wait, fetches the new clone key and updates it (team field for BUG, assignee for others).

**PIC assignment priority:**
1. `by_game_id` match on `game_id` (most specific)
2. `fallback.devops` if `ticket_type == "DevOps Support"`
3. `fallback.general` (catch-all)

**Destination boards:**

| Board | Clone target | Condition |
|-------|-------------|-----------|
| `PORTFOLIO` | PACT Portfolio project | New requests / planned work |
| `BUG_TRACKER` | Bug Tracker project | Bugs and production incidents |
| `DEVOPS` | DevOps project | CI/CD, provisioning, infrastructure |
| `RNG` | RNG Task project | Cheat tool access, build environments |
| `BO` | *(no clone)* | Back Office / platform config |

---

### POST `/scan`
**Trigger:** Issue created or comment added.

**What it does:** Detects PII, legal threats, and sensitive content. Posts an internal flag comment and notifies team lead via GChat if flagged.

---

### POST `/rewrite`
**Trigger:** Status transition → Approved.

**What it does:** Rewrites the ticket as a developer task — generates `dev_summary`, `dev_description`, and `acceptance_criteria`. Posts result as an internal comment. (Jira Automation handles the actual clone to the dev board.)

---

### POST `/summarise`
**Trigger:** Scheduled every 4 hours by Jira Automation.

**What it does:** Analyses a ticket for staleness. If stale, posts a nudge comment and sends a summary to the ops GChat space. Detects user frustration in comments.

---

### POST `/detect`
**Trigger:** Linked issue status changes.

**What it does:** Identifies overdue or blocked linked issues. Posts a reminder comment on the parent ticket and notifies the developer via GChat.

---

## Admin API

```bash
# Health check
curl http://localhost:8080/admin/health -H "X-Agent-Key: your-key"

# Get current mode
curl http://localhost:8080/admin/mode -H "X-Agent-Key: your-key"

# Set mode
curl -X POST http://localhost:8080/admin/mode \
  -H "X-Agent-Key: your-key" -H "Content-Type: application/json" \
  -d '{"mode": "on"}'   # on | test | off

# Manually re-trigger triage (for tickets missed during downtime)
curl -X POST http://localhost:8080/admin/triage \
  -H "X-Agent-Key: your-key" -H "Content-Type: application/json" \
  -d '{"issue_key": "SUP-123", "game_id": "1969"}'
```

> `game_id` is not a standard Jira field — pass it in the request body if known, otherwise the agent falls back to the general PIC with a ⚠️ warning.

---

## Testing

Run from the **project root** (not `scripts/`):

```bash
source venv/bin/activate
pytest                          # all 139 tests
pytest tests/test_utils.py      # single file
pytest -k "test_triage_mode"    # single test by name
```

`conftest.py` stubs the `gemini` module (no GCP needed), mocks `pic_config` loading for all tests except `test_pic_config.py`, and auto-resets mode state and failure counts between every test.

**Manual test against real Jira:**
```bash
curl -X POST http://localhost:8080/triage \
  -H "Content-Type: application/json" \
  -H "X-Agent-Key: your-key" \
  -d '{
    "issue_key": "SUP-123",
    "summary": "Cannot login",
    "description": "403 since this morning",
    "reporter": "Dante",
    "ticket_type": "Bug",
    "game_name": "Dragon Quest",
    "environment": "prod",
    "game_id": "1969"
  }'
```

---

## Deploying to Cloud Run (Phase 4)

```bash
gcloud run deploy jira-agent --source . --region asia-southeast1
gcloud run services logs read jira-agent --region asia-southeast1 --tail=50
```

**Pending Phase 4 items before multi-instance deploy:**
- **Firestore:** Migrate `mode_state` in `admin.py` from an in-memory dict to Firestore. Currently, a mode change on one container instance does not propagate to others.
- **Secret Manager:** Migrate all `.env` secrets to GCP Secret Manager and inject via Cloud Run environment variable references.

---

## Security Model

- **Auth:** Every endpoint validates `X-Agent-Key` header using constant-time comparison (`hmac.compare_digest`).
- **Prompt injection:** All user-supplied text (`summary`, `description`, `reporter`, `game_id`, `linked_issues`, etc.) passes through `utils.sanitise()` before use in any Gemini prompt. Patterns such as `"ignore all previous instructions"` and `"act as"` are stripped.
- **Structural separation:** User data is wrapped in XML tags inside prompt templates (e.g. `<description>…</description>`) to separate it structurally from prompt instructions.
- **Secrets:** `.env` and `credentials/` are `.gitignore`d. Never commit them.

---

## Module Reference

| File | Responsibility |
|------|---------------|
| `scripts/main.py` | Flask routes, background thread orchestration, mode-aware action dispatch |
| `scripts/gemini.py` | Vertex AI client (`google-genai` SDK, `gemini-2.5-flash`, global endpoint) |
| `scripts/jira.py` | Singleton `JiraV3Client`; Jira REST API v3 — updates, comments, transitions, links |
| `scripts/pic_config.py` | Google Sheets PIC config loader; 5-min TTL cache with threading lock |
| `scripts/admin.py` | Flask Blueprint for `/admin/mode`, `/admin/health` |
| `scripts/utils.py` | `sanitise()`, `load_prompt()`, `parse_gemini_json()`, `verify_key()` |
| `scripts/reporter.py` | Always-on Agent Report cards to GChat audit space; tracks per-flow failure counts |
| `scripts/gchat.py` | Business notification cards to ops GChat space (suppressed in `test`/`off` mode) |
| `prompts/*.txt` | Gemini prompt templates; use `{{key}}` placeholders, not Python f-strings |

---

## Files to Transfer Manually

These are excluded from Git and must be copied manually when moving to a new machine or server:

| File/Folder | Contents |
|-------------|---------|
| `.env` | All secrets and configuration values |
| `credentials/` | GCP service account JSON key file (directory must be created manually) |
