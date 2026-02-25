---
id: loo-oizg
status: open
deps: [loo-5s8p]
links: []
created: 2026-02-25T01:22:42Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 11: Act Creation

Any player proposes a new act with a guiding question. Goes through voting/approval. On approval, the act becomes active.

## Acceptance Criteria

### REQ-ACT-001: Act Creation
*Requirement:* When the game is active, Loom shall allow players to propose a new act with a guiding question.
*Acceptance Criteria:*
- Any player can propose a new act.
- The proposal includes a title (optional) and a guiding question (required) - e.g., "Who is behind the disappearances in the Rusted Quarter?"
- Act creation is treated as a major beat and requires group approval via the standard voting mechanism.
- The AI can suggest possible guiding questions based on unresolved threads in the fiction.
- Only one act can be active at a time.

---

### REQ-VOTE-001: Voting Mechanics
*Requirement:* When a major beat, scene transition, act transition, or other significant proposal is submitted, Loom shall manage a voting process.
*Acceptance Criteria:*
- The proposer's submission counts as an implicit "yes" vote.
- The threshold for approval is more than half of all players in the game (e.g., in a 3-player game, 2 votes needed; in a 4-player game, 3 votes needed; in a 5-player game, 3 votes needed).
- In a 2-player game, the other player must explicitly approve major proposals.
- Players can vote yes, no, or suggest a modification.
- Votes and suggestions are visible to all players.

---

### REQ-VOTE-002: Silence is Consent
*Requirement:* When a major beat or other proposal requiring a vote has been open for the configured silence timer duration without reaching a rejection threshold, Loom shall auto-approve it.
*Acceptance Criteria:*
- This applies to major beats, scene/act proposals, and other items that go through the voting flow. Minor beats are canon immediately and do not use the silence timer.
- The silence timer is configurable per game (default: 12 hours).
- If the timer expires and the proposal has not been explicitly rejected by enough players to block it, it is automatically approved and moves to canon status.
- Players are notified when auto-approval occurs.
- The timer resets if a modification is suggested (giving the proposer time to revise).

