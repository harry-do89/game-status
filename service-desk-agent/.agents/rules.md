# Jira AI Agent — Build Rules and Directions

These rules dictate how to build, test, and deploy the Jira AI Service Desk Agent. They are extracted directly from the v2 Implementation Plan and must be followed strictly to ensure security, reliability, and observability.

## 1. Development Workflow
* **Local First:** Build and test everything locally via `curl` before wiring Jira.
* **No Jira Touches Yet:** Do not configure Jira Automation until the Flask endpoints return `{"status": "accepted"}` locally in under 200ms and background writes succeed.
* **Test Mode Default:** Always start the agent in `test` mode. Only switch to `on` mode after verifying logs and Agent Report cards.

## 2. Core Architectural Requirements
* **Async Pattern (Mandatory):** Jira Automation has a strict 5-second timeout. To bypass this, the Flask app MUST return `HTTP 202 Accepted` immediately upon receiving a webhook, and process the Vertex AI (Gemini) call in a background thread (`threading.Thread`).
* **Direct Jira Writes:** Because of the async pattern, Jira Automation cannot use webhook response bodies to edit fields. The Flask agent MUST use the Jira REST API (`jira.py`) to write back updates directly.
* **Admin Mode:** The agent must respect three modes:
  * `on`: Gemini runs, Jira writes, Chat notifications sent.
  * `test`: Safe dry-run. Gemini runs, logs generated, but Jira writes and business Chats are suppressed.
  * `off`: Instant shutdown. Returns HTTP 200 no-op, skipping Gemini entirely.
  * *Note for Phase 4:* Cloud Run requires Firestore to maintain shared `Admin Mode` state across multiple container instances.

## 3. Security & Safety
* **Prompt Injection Defense:** All user-submitted text (summary, description, comments) MUST be passed through a `sanitise()` function to scrub common injection phrases (e.g., "ignore previous instructions").
* **XML Fencing:** Sanitized user inputs must be wrapped in XML tags (e.g., `<description>...</description>`) within the Gemini prompt templates to separate data from instructions.
* **Safe Defaults:** Every endpoint must catch exceptions gracefully. If Gemini fails or times out, the app must not crash the Jira Automation workflow.

## 4. Observability
* **Agent Report Space:** A dedicated Google Chat space acts as the audit trail. A report card MUST be sent for **every** request, regardless of whether the agent is `on`, `test`, or `off`.
* **Failure Alerts:** The system must track failures per flow. If a flow fails 3 times consecutively, a `🚨 CRITICAL` alert must be sent to the Agent Report space immediately.

## 5. Deployment Constraints (Phase 4)
* **Secret Manager:** Local `.env` variables (Agent key, Jira tokens, Webhook URLs) must be migrated to GCP Secret Manager for Cloud Run deployment.
* **Cloud Run Cold Starts:** While the async pattern mitigates the 5s timeout, consider using `--min-instances=1` for critical production environments to avoid cold starts entirely.
