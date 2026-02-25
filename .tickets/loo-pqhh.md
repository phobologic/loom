---
id: loo-pqhh
status: open
deps: []
links: []
created: 2026-02-25T02:29:26Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:security]
---
# Invite token stored on Game row enables timing side-channel and token enumeration

**File**: loom/models.py, loom/routers/games.py | **Line(s)**: models.py:183, games.py:127,165 | **Description**: The invite token is stored in plaintext on the Game row and looked up with a simple equality WHERE clause (Game.invite_token == token). SQLAlchemy's default String comparison is not constant-time, creating a potential timing oracle. Also, since the token is on the Game row, any code path that loads a Game object exposes the token value to all members, not just the organizer. | **Suggested Fix**: Use hmac.compare_digest for token comparison. Consider moving the token to the Invitation table (which already exists) and querying that table instead of the Game row directly. The Invitation model already has is_active and used_by_id fields that support revocation semantics.

