# Phase 0 Context — Prerequisites Tracking

**Goal:** Set up the environment and cloud infrastructure required to build and test the Jira AI Service Desk Agent.

## Progress Checklist

### 0.1 Local Environment
- [x] Install Homebrew: `brew install`
- [x] Install Python 3.12+: `brew install python` (Installed 3.14)
- [x] Install ngrok: `brew install ngrok`
- [ ] VS Code installed
- [x] Gemini Code Assist extension installed and signed in

### 0.2 ngrok Setup
- [x] Sign up at ngrok.com
- [x] Authenticate ngrok: `ngrok config add-authtoken <token>`

- [x] Create GCP Project: `jira-agent-personal`
- [x] Enable Billing
- [x] Enable Vertex AI API
- [x] Create Service Account: `agent-platform`
- [x] Assign Role: `Vertex AI User`
- [x] Download `credentials.json` (Stored in credentials/ folder)
- [x] Install gcloud SDK: `brew install google-cloud-sdk` (Installed via cask)
- [x] Authenticate gcloud: `gcloud auth login`

### 0.4 Google Chat Webhooks
- [x] Webhook 1 (Ops Space): `Jira Agent`
- [x] Webhook 2 (Agent Report Space): `Agent Reporter`

---

## Actions Taken
- **2026-04-30**: Initialised `context/phase_0.md` to track prerequisites.
- **2026-04-30**: USER installed Homebrew, Python 3.14, gcloud-cli, and ngrok.
- **2026-04-30**: USER completed GCP project setup, service account creation, and Chat webhook creation. Phase 0 is COMPLETE.
