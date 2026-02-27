---
id: loo-ewgh
status: closed
deps: []
links: []
created: 2026-02-27T05:31:31Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-jy09
---
# Step 40: Game Organizer Admin Features

The full organizer role beyond role assignment (which was covered in Phase 1 Step 4). The organizer can remove a player from the game, pause a game, resume a paused game, and archive a game (making it read-only but still viewable). All organizer actions are visible to all players. The organizer has no special narrative authority.

## Requirements

### REQ-GAME-003: Game Organizer Role
*Requirement:* The game creator shall have an "organizer" role with administrative (but not narrative) privileges.
*Acceptance Criteria:*
- The organizer can adjust game settings (timers, voting thresholds, tie-breaking rules, significance defaults) after creation.
- The organizer can remove a player from the game.
- The organizer can pause or archive a game.
- The organizer has no special narrative authority — they cannot override votes, auto-approve their own beats, or skip challenges.
- All organizer actions are visible to all players.

### REQ-GAME-005: Game States
*Requirement:* Loom shall track game state through a defined lifecycle.
*Acceptance Criteria:*
- Game states: setup (Session 0 in progress), active (play in progress), paused, archived.
- Only the organizer can pause or archive a game.
- A paused game can be resumed by the organizer.
- An archived game is read-only but still viewable.

