---
id: loo-bybi
status: in_progress
deps: [loo-86qv]
links: []
created: 2026-02-25T01:22:43Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 17: Beat Significance Classification

AI suggests major/minor (stubbed — stub always returns 'minor'), player accepts or overrides. Major beats enter the voting flow. Full beat lifecycle state machine is now active.

## Acceptance Criteria

### REQ-BEAT-003: Beat Lifecycle
*Requirement:* Loom shall manage beats through a defined lifecycle.
*Acceptance Criteria:*
- Beat statuses: proposed, canon, challenged, revised, rejected.
- When a minor beat is submitted, it becomes canon immediately. No approval gate or waiting period is required. Other players can challenge it after the fact if needed.
- When a major beat is submitted, it enters "proposed" status and requires explicit approval via voting. The silence timer applies only to major beats.
- Any player can challenge a canon beat, moving it to "challenged" status.
- A challenged beat can be revised by the original author (status: revised, then re-enters the approval flow as a major beat) or rejected by group vote.

---

### REQ-BEAT-004: Beat Significance Classification
*Requirement:* When a player submits a beat, Loom shall classify it as major or minor.
*Acceptance Criteria:*
- The AI analyzes the beat content and suggests a significance level based on factors such as: introducing a new named character, changing location, involving conflict or violence, revealing significant information, altering established world facts, or proposing a scene/act transition.
- The suggestion is shown to the submitting player before submission (e.g., "This seems like a major beat - put it up for group input?").
- The player can accept or override the AI's suggestion.
- The significance threshold is configurable per game (see REQ-GAME-004).
- Minor beats follow the silence-is-consent auto-approval path.
- Major beats require active voting.

NOTE: AI classification is stubbed in this step. Stub always returns "minor".

