---
id: loo-t6ld
status: open
deps: [loo-j8vl]
links: []
created: 2026-02-25T01:22:43Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 20: Oracle - Discussion + Selection

Vote on interpretations, comment, propose alternatives. Invoker makes final selection. Selected interpretation can be woven into a beat.

## Acceptance Criteria

### REQ-ORACLE-003: Oracle Interaction Flow
*Requirement:* When oracle interpretations have been generated, Loom shall allow collaborative discussion and selection.
*Acceptance Criteria:*
- All players can see the generated interpretations.
- Players can vote on an interpretation.
- Players can comment on an interpretation.
- Players can propose their own alternative interpretation.
- The player who invoked the oracle makes the final selection, informed by votes, comments, and alternatives.
- If the oracle result affects only the invoking player's character (personal oracle), they can select without group input.
- If the oracle result affects the shared fiction (world oracle), the collaborative flow is used.

---

### REQ-ORACLE-004: Oracle Vote Tie-Breaking
*Requirement:* When oracle votes result in a tie, Loom shall resolve it according to the game's configured tie-breaking method.
*Acceptance Criteria:*
- Tie-breaking methods: random (roll a die between tied options - default), proposer decides, challenger decides.
- The tie-breaking method is configurable per game.
- All tie-breaking methods are available as configuration options.

