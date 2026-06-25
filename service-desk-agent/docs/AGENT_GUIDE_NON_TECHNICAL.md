# PACT Triage Agent — How It Works
### A Guide for Non-Technical Team Members

---

## What Is the PACT Triage Agent?

The PACT Triage Agent is an AI assistant that automatically processes every new support ticket submitted to the PACT Service Desk. Instead of a human manually reading each ticket, deciding its priority, figuring out which team should handle it, and then notifying that team — the agent does all of this within seconds of the ticket being created.

Think of it as a smart receptionist that never sleeps: it reads every incoming request, decides where it needs to go, assigns the right person, and notifies the right team — all automatically.

---

## What Triggers the Agent?

The agent is connected to Jira Service Management (JSM). It activates automatically when:

| Event | What the agent does |
|-------|-------------------|
| A new ticket is created | Classifies it, assigns a PIC, routes it to the correct team |

---

## The Journey of a Ticket

When a support ticket is submitted, here is what happens step by step:

```
1. Customer submits ticket in JSM portal
         ↓
2. Agent reads the ticket (summary, description, game ID, request type)
         ↓
3. AI (Gemini) analyses the ticket and decides:
   • Priority (Critical / High / Medium)
   • Which board to send it to (Bug Tracker, Portfolio, DevOps, RNG Task, Back Office)
   • Category and confidence level
         ↓
4. Agent updates the ticket in Jira:
   • Sets the priority
   • Assigns the correct PIC (Person in Charge)
   • Posts an internal note with the triage summary
         ↓
5. Agent creates a clone of the ticket on the destination team board
         ↓
6. Agent notifies the team via Google Chat
         ↓
7. Agent posts a report card to the Admin Audit space
```

The entire process takes about 10–15 seconds.

---

## How Does the Agent Know Who to Assign?

Assignment is based on the **Game ID** field in the ticket. Each game is mapped to a specific team and a PIC (Person in Charge) in a configuration spreadsheet (Google Sheets).

**Priority order:**

1. **Game ID match** — if the ticket has a known Game ID, it goes directly to the team and PIC configured for that game
2. **DevOps tickets** — any ticket the AI routes to the DevOps board (or with request type "DevOps Support") is automatically assigned to the DevOps fallback PIC, skipping game ID lookup entirely
3. **No match / missing Game ID** — assigned to the general fallback PIC, and a ⚠️ warning appears in the report card

> If you notice ⚠️ warnings appearing frequently for a specific game, it means that game's ID is not yet in the configuration sheet. Contact the system administrator to add it.

---

## What the Team Sees

### 1. Google Chat Notification (your team's space)

When a ticket is assigned to your team, a card appears in your team's Google Chat space:

```
🎫 New ticket assigned
─────────────────────────────
Ticket:      SUP-612 (clickable link)
Summary:     Game crashes on login screen
Description: Players receive error 403 since 9am
Game ID:     1969
Priority:    Critical
```

### 2. Jira Ticket Updates

Opening the ticket in Jira, you will see:
- **Priority** has been set automatically
- **Assignee** has been set to the PIC for that game
- An **internal note** (visible to agents only, not the customer) with the full triage decision, including which board it was routed to and why

### 3. Cloned Task on Your Team Board

A copy of the ticket appears on your team's board (Bug Tracker, Portfolio, DevOps, or RNG Task) — ready to be worked on.

---

## What the Agent Can Do

### Triage (classify & route)
Every new ticket → classified by AI → priority set → PIC assigned → routed to correct board → team notified.

**Automatic priority rules (override AI decision):**

| Request Type | Priority forced to |
|---|---|
| Production Incident | Critical |
| Production Support | Critical |

These override whatever the AI decides based on content — no exceptions.

---

## The Declined Path

The agent will automatically **decline** tickets that are not submitted in English.

When declined:
- A polite message is posted on the ticket explaining it was declined
- The ticket is automatically moved to **"Decline"** status
- No further triage happens

This ensures the service desk only processes tickets submitted in English.

---

## The Admin Report Card

After every action, the agent sends a detailed **report card** to the Admin Audit space in Google Chat. This is always sent regardless of whether the agent is in live mode or test mode.

The report card shows:
- Which ticket was processed
- What the AI decided (priority, board, category, confidence)
- What actions were taken (assignee set, comment posted, clone created, team notified)
- How long it took
- Any warnings or errors

This is the audit trail — useful for checking why a ticket was routed a certain way, or investigating if something went wrong.

---

## Agent Modes

The agent has three operating modes. The current mode is shown on every report card.

| Mode | What it means |
|------|--------------|
| **ON** | Fully active. Updates Jira, sends all notifications, creates clones. |
| **TEST** | AI runs and decisions are logged, but nothing is written to Jira and no notifications are sent. Used for testing. |
| **OFF** | Agent is paused. All incoming requests are acknowledged but not processed. |

The default mode when the agent starts is **TEST**. The system administrator switches it to **ON** when ready for live use.

---

## What Happens If the Agent Makes a Mistake?

The agent includes a confidence score with every decision. If you notice a ticket was routed to the wrong board or assigned the wrong priority:

1. The ticket can be manually corrected in Jira — the agent does not lock any fields
2. The triage can be re-run manually by the system administrator for any ticket that was missed or incorrectly processed
3. Check the Admin Audit space in Google Chat for the report card on that ticket to see exactly what the AI decided and why

The AI is not perfect — it relies on the quality of the ticket's summary and description. Tickets with very short or vague descriptions may receive lower confidence scores.

---

## Configuration: The Google Sheet

The PIC assignment rules live in a Google Sheet maintained by the system administrator. It has three tabs:

---

### Tab 1 — `fallback`

Defines all PICs and which one is the default assignee when no game ID match is found.

| Column | Description | Can edit? |
|--------|-------------|-----------|
| `pic_name` | Display name shown in notifications and report cards | ✅ Yes |
| `pic_email` | Jira account email — must match exactly | ⚠️ Only if email changed |
| `pic_account_id` | Jira internal account ID — used for assignment | ❌ Do not edit (must match Jira) |
| `role` | `general` = default fallback, `devops` = DevOps fallback, blank = regular PIC | ⚠️ Do not change unless reassigning fallback role |

> There must always be exactly **one row with `role = general`** and **one row with `role = devops`**. Removing or duplicating these breaks assignment.

---

### Tab 2 — `by_game_id`

Maps each Game ID to a team and PIC. **This is the tab you will edit most often.**

| Column | Description | Can edit? |
|--------|-------------|-----------|
| `game_id` | The Game ID as it appears in the JSM ticket field | ❌ Do not change (must match exactly) |
| `team_name` | Display name of the team | ✅ Yes |
| `team_id` | Jira team UUID — used to assign the team on the cloned task | ❌ Do not edit (must match Jira) |
| `pic_email` | Email of the PIC for this game — must exist in the `fallback` tab | ✅ Yes (to reassign) |
| `active` | `TRUE` = this rule is active, `FALSE` = ignored by agent | ✅ Yes |

**When to add a new row:**
- A new game is onboarded and starts submitting tickets to the service desk
- You notice ⚠️ warnings in the Admin Audit space for a game ID that is not yet listed

**How to add a new game:**
1. Get the Game ID from the JSM ticket (the value in the "Game ID" field)
2. Get the team's Jira team UUID from the system administrator
3. Add a new row with all five columns filled in and `active = TRUE`
4. Changes take effect within 5 minutes — no restart required

**To deactivate a game** (e.g. game is retired): set `active = FALSE`. Do not delete the row.

---

### Tab 3 — `special_rules`

Feature flags that turn agent behaviours on or off.

| Column | Description | Can edit? |
|--------|-------------|-----------|
| `rule_name` | Internal rule identifier | ❌ Do not edit |
| `enabled` | `TRUE` or `FALSE` | ✅ Yes |
| `notes` | Description of what the rule does | ✅ Yes (documentation only) |

Current rules:

| Rule | What it does |
|------|-------------|
| `vnd_vietnamese_detection` | When `TRUE`, tickets not submitted in English are automatically declined |

---

> **Important:** Never add or remove columns in any tab. Never rename column headers. The agent reads columns by position — changing the structure will cause it to misread the data.

---

## Frequently Asked Questions

**Q: Why did a ticket get assigned to the wrong person?**
The ticket's Game ID was either missing or not found in the configuration sheet. The agent falls back to the general PIC and adds a ⚠️ warning in the report card. Check the Admin Audit space for that ticket.

**Q: Why did a ticket not get processed?**
Possible reasons: the agent was in TEST or OFF mode, the Game ID field was blank, or the agent encountered an error. Check the Admin Audit space — a report card is always sent even for errors.

**Q: Can the agent process a ticket that was missed?**
Yes. The system administrator can manually re-trigger triage for any ticket using its ticket key (e.g. SUP-123).

**Q: Will the agent post public comments that customers can see?**
The triage note posted by the agent is an **internal comment** — customers cannot see it. Only the "Declined" message (when applicable) is posted as a public reply.

**Q: How do I know which team was notified?**
Check your team's Google Chat space for the notification card, or check the Admin Audit space report card which lists every action taken including which clone was created.
