---
id: loo-5s8p
status: closed
deps: [loo-nv8x]
links: []
created: 2026-02-25T01:22:42Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 10: Game Dashboard - Full Content

The game dashboard shell (introduced in Step 4) is now populated with real content: game state, members, link to world document, list of acts, active act and its scenes. The player's home base for the game.

## Acceptance Criteria

### REQ-GAME-005: Game States
*Requirement:* Loom shall track game state through a defined lifecycle.
*Acceptance Criteria:*
- Game states: setup (Session 0 in progress), active (play in progress), paused, archived.
- Only the organizer can pause or archive a game.
- A paused game can be resumed by the organizer.
- An archived game is read-only but still viewable.

