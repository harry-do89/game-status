# Phase 2 Context — Wire Jira Automation (local + ngrok)

**Goal:** Jira Automation calling the local Flask app via ngrok. Full end-to-end flows working before any cloud deployment.

## What was done

### ngrok
- ngrok started (`ngrok http 8080`) to expose local Flask server to Jira Cloud.
- Public URL updated in all 5 Jira Automation rules each session (changes on free plan restart).

### Jira Automation rules created
All 5 rules configured as single "Send web request" actions — agent handles all write-backs directly via `jira.py`.

| Rule | Trigger | Endpoint | Status |
|------|---------|----------|--------|
| ① Triage new ticket | Issue created | `POST /triage` | ✅ Wired + tested |
| ② Sensitive scan | Issue created / comment added | `POST /scan` | ⬜ Not end-to-end tested |
| ③ Clone to dev board | Status → Approved | `POST /rewrite` | ⬜ Not end-to-end tested |
| ④ Stale ticket monitor | Scheduled every 4h | `POST /summarise` | ⬜ Not end-to-end tested |
| ⑤ Linked item reminder | Linked issue status changed | `POST /detect` | ⬜ Not end-to-end tested |

### JSM fields aligned
- `prompts/summarise.txt` updated to match JSM field names from `prompts/triage.txt`.
  - Changed board names in CONTEXT section to: `PACT PORTFOLIO`, `BUG TRACKER`, `DEVOPS`.
  - `process_summarise()` now extracts all 12 prompt variables from JSM payload.
  - Mode dispatch uses `result.get("is_stale")` (not the old `urgency != "low"` check).

### Key design decision confirmed
Jira Automation handles the clone (flow ③). Flask `/rewrite` only rewrites the text and writes `dev_summary` / `dev_description` to JSM custom fields. JA reads those fields via smart values to create the dev board issue.

## End-to-end test checklist status

### Test mode (no business impact)
- [x] Triage: test ticket created → Gemini result in logs, NO Jira field changes, NO ops Chat notification
- [x] Agent Report space: triage report card appears showing `TEST MODE` and suppressed actions
- [ ] Scan: comment with email address → scan result in logs, no internal comment posted
- [ ] Agent Report space: scan report card appears
- [ ] Rewrite: ticket transitioned to Approved → rewrite result in logs, no dev board issue created
- [ ] Agent Report space: rewrite report card shows dev_summary preview
- [ ] Summarise: scheduled rule triggered manually → no comments posted
- [ ] Agent Report space: summarise report card shows urgency and recommended action
- [ ] Detect: linked dev issue status updated → no Chat DM sent
- [ ] Agent Report space: detect report card shows blocked issues

### On mode (live)
- [x] Mode switched to `on` via `curl -X POST .../admin/mode`
- [x] Triage: test ticket created → Jira fields updated + internal note added
- [x] Agent Report space: report shows `✅ Jira fields updated` and `✅ Jira Automation: Triggered Clone`
- [ ] Scan: comment with "legal threat" → internal flag comment appears on ticket
- [ ] Rewrite: ticket to Approved → dev board issue created, linked back, Chat card in dev space
- [ ] Summarise: scheduled rule → stale tickets get nudge comment
- [ ] Detect: linked dev issue status update → parent flagged + Chat DM to developer

### Off mode
- [ ] `off` mode: ticket created → nothing happens in Jira or ops Chat
- [ ] Agent Report space: `🔴 Agent OFFLINE` card appears

## Next steps before Phase 3
- Complete end-to-end tests for flows ②③④⑤ in both `test` and `on` modes.
- Verify `off` mode suppresses everything but the Agent Report card.
