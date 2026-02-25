---
id: loo-ad8u
status: closed
deps: [loo-vyev]
links: []
created: 2026-02-25T01:22:41Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 5: Game Settings

The organizer can view and edit game settings. All configurable values with their defaults. Other players can view but not edit.

## Acceptance Criteria

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

