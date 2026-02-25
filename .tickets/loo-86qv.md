---
id: loo-86qv
status: closed
deps: [loo-fy6b]
links: []
created: 2026-02-25T01:22:43Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 16: Dice Rolling

Dice rolling within roll events. Standard notation parsing, server-side execution, result display in the timeline.

## Acceptance Criteria

### REQ-DICE-001: Inline Dice Rolling
*Requirement:* Loom shall allow players to roll dice as part of a beat submission.
*Acceptance Criteria:*
- Players can include one or more dice rolls in a beat using standard notation (e.g., 2d6+1, 1d20, 3d10-2).
- The roll is executed server-side and the result is displayed as a roll event within the beat.
- The roll result is visible to all players.
- A reason/label can optionally be attached to each roll.

---

### REQ-DICE-002: Roll Interpretation by Players
*Requirement:* Loom shall leave interpretation of roll results to the players, not the AI.
*Acceptance Criteria:*
- Loom displays the numeric result but does not interpret success/failure or narrative outcome.
- Players interpret what the roll means in the fiction via narrative events within the same beat, subsequent beats, or by calling the oracle for suggestions.
- Loom does not enforce any specific game system's success criteria.

