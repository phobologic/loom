---
id: loo-vyev
status: closed
deps: [loo-2d5u]
links: []
created: 2026-02-25T01:22:41Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 4: Game Creation + Joining + Dashboard Shell

Create a game (name + optional pitch), get an invite link, join via invite link, see a game lobby showing current members. Organizer role assigned on creation. Player cap enforced.

Also establishes the **skeleton game dashboard**: a persistent frame showing game name, current state, member list, and placeholder nav links (acts, settings, world doc). All subsequent steps wire into this shell. The dashboard fills in as later steps add content.

## Acceptance Criteria

### REQ-GAME-001: Game Creation
*Requirement:* When a user wants to start a new game, Loom shall allow them to create a game with a name and an initial pitch or description.
*Acceptance Criteria:*
- The creator provides a game name (required) and a pitch/description (optional).
- The creator becomes a member of the game with the "organizer" role.
- The game is private by default.
- The game is created in a "setup" state, ready for Session 0.

---

### REQ-GAME-002: Game Invitation
*Requirement:* When a game has been created, Loom shall generate a shareable invite link that the organizer can distribute to other players.
*Acceptance Criteria:*
- The invite link is unique to the game.
- Any authenticated user with the link can join the game, up to 5 total players.
- Loom rejects joins that would exceed 5 players.
- The organizer can regenerate or revoke the invite link.

---

### REQ-GAME-003: Game Organizer Role
*Requirement:* The game creator shall have an "organizer" role with administrative (but not narrative) privileges.
*Acceptance Criteria:*
- The organizer can adjust game settings (timers, voting thresholds, tie-breaking rules, significance defaults) after creation.
- The organizer can remove a player from the game.
- The organizer can pause or archive a game.
- The organizer has no special narrative authority - they cannot override votes, auto-approve their own beats, or skip challenges.
- All organizer actions are visible to all players.

NOTE: Step 4 covers role assignment only. Full organizer capabilities are built across subsequent steps.

