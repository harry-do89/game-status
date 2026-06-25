# Phase 1 Context — PACT Triage Agent Implementation

**Goal:** Automate the triage, routing, and cloning of incoming Jira Service Management (JSM) tickets using Gemini 1.5 Flash and a robust Jira v3 integration.

## Capabilities Overview

### 1. Intelligent Triage (Gemini 1.5 Flash)
- **Automatic Analysis**: Parses incoming ticket summaries and descriptions to determine:
    - **Priority**: (Critical, High, Medium, Low) based on impact and urgency.
    - **Request Type**: (Bug, Support, New Game, Change Request, etc.)
    - **Destination Board**: Routes to `PACT PORTFOLIO` or `BUG TRACKER`.
    - **Suggested Teams**: Identifies involved teams (e.g., Math, RNG, BO, Backend).
- **Triage Notes**: Generates a professional reasoning note for every decision.
- **Production Incident Detection**: Specifically flags live production issues.

### 2. Live Jira Integration (Jira v3 Core)
- **Field Updates**: Automatically updates Priority and Labels in real-time.
- **Internal Notes (JSM)**: Posts triage decisions as official "Internal Notes" in the JSM portal (not visible to customers).
- **Refined Security**: Implements `JiraV3Client` with session-based authentication and connection pooling.

### 3. Automated Cloning Workflow
- **Webhook Triggers**: Communicates with Jira Automation to clone tickets to secondary boards.
- **Secure Communication**: Uses URL-path tokens (`/[secret]`) to bypass Atlassian security restrictions.
- **Asynchronous Link Detection**: Waits for the clone to be created and retrieves the new ticket ID (e.g., `PACT-XXX`, `BUG-XXX`).

### 4. Premium GChat Reporting
- **Interactive Cards**: Sends rich, formatted cards to a dedicated Google Chat space.
- **Smart Hyperlinking**: Automatically converts all mentioned Jira keys (Original and Cloned) into clickable links.
- **Team Acronym Preservation**: Ensures "RNG" and "BO" teams are always correctly cased in reports.
- **Duration Tracking**: Monitors agent performance latency (ms).

---

## Technical Stack
- **Core**: Python 3.14 (Flask)
- **AI**: Google Gemini 1.5 Flash (Vertex AI)
- **Tunneling**: ngrok (Public endpoint for Jira Cloud webhooks)
- **Authentication**: `X-Agent-Key` for incoming requests; JQL-based Jira v3 API for outbound actions.

## Milestone Status
- [x] Core Triage Logic Implementation
- [x] Jira v3 Skill Refactor
- [x] JSM Internal Note Integration
- [x] Automated Webhook Clone Flow
- [x] Clickable GChat Reports

---

## Next Steps / Future Enhancements
- **Multi-Team Slack/GChat Notifications**: Routing specific alerts to team-specific channels.
- **Historical Learning**: Tuning the triage prompt based on past human decisions.
- **Sentiment Analysis**: Detecting frustrated customers early in the triage phase.
