---
id: loo-i3rj
status: open
deps: [loo-bybi]
links: []
created: 2026-02-25T01:22:43Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 18: Voting - Full Implementation + Silence Timer

Complete voting system. Threshold calculation, yes/no/suggest modification, vote display, tie-breaking configuration. Silence timer included: configurable duration, countdown display, auto-approval on expiry, player notification when auto-approval fires. Timer resets if a modification is suggested.

The minimal voting introduced in Step 8 is replaced/upgraded here.

## Acceptance Criteria

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

---

### REQ-GAME-004: Game Settings
*Requirement:* Loom shall provide configurable settings per game, with sensible defaults.
*Acceptance Criteria:*
- Configurable settings include:
  - Silence timer duration (default: 12 hours) - how long before uncontested major beats auto-approve.
  - Voting threshold: majority of all players (default, non-configurable formula, but the timer is adjustable).
  - Tie-breaking method (options: random/die roll, proposer decides, challenger decides; default: random).
  - Beat significance threshold (options: flag most things as major, only flag obvious things, minimal flagging; default: only flag obvious things).
  - Maximum consecutive beats per player before soft spotlight nudge (default: 3).
  - Auto-generate narrative on scene/act completion (default: on).
  - Fortune Roll odds contestation window (default: half the silence timer or 1 hour minimum).
  - Starting Tension for new acts (default: 5).
- Settings can be changed by the organizer at any time.
- Changes to settings are visible to all players.

