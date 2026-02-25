---
id: loo-fy6b
status: closed
deps: [loo-r09h]
links: []
created: 2026-02-25T01:22:43Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 15: Beat Submission - Multi-Event

Extend the beat composer to support multiple events of different types in a single beat. Narrative, OOC, and rolls (without dice rolling yet). Primarily a UI/interaction design step.

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

