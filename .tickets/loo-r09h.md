---
id: loo-r09h
status: open
deps: [loo-hp0m]
links: []
created: 2026-02-25T01:22:42Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 14: Beat Submission - Narrative Only

Compose and submit a beat with a single narrative event. Appears in the timeline. All beats treated as minor (instant canon) for now.

## Acceptance Criteria

### REQ-BEAT-001: Beat Submission
*Requirement:* When a scene is active, Loom shall allow any player to submit a beat.
*Acceptance Criteria:*
- A beat is authored by a single player.
- A beat contains one or more events (see REQ-EVENT).
- Players can write in shorthand/bullets - polished prose is never required.
- A beat is submitted as a proposal with a lifecycle (see REQ-BEAT-003).

---

### REQ-BEAT-002: Event Types
*Requirement:* Loom shall support the following event types within a beat.
*Acceptance Criteria:*
- **Narrative**: An in-character action, description, or dialogue.
- **Roll**: A dice roll with notation, result, and optional reason (see REQ-DICE).
- **Oracle**: An oracle query and its results (see REQ-ORACLE).
- **OOC**: An out-of-character comment, question, or discussion point.
- A single beat can contain multiple events of different types.
- Events within a beat are ordered.

---

### REQ-BEAT-003: Beat Lifecycle
*Requirement:* Loom shall manage beats through a defined lifecycle.
*Acceptance Criteria:*
- Beat statuses: proposed, canon, challenged, revised, rejected.
- When a minor beat is submitted, it becomes canon immediately. No approval gate or waiting period is required. Other players can challenge it after the fact if needed.
- When a major beat is submitted, it enters "proposed" status and requires explicit approval via voting. The silence timer applies only to major beats.
- Any player can challenge a canon beat, moving it to "challenged" status.
- A challenged beat can be revised by the original author (status: revised, then re-enters the approval flow as a major beat) or rejected by group vote.

