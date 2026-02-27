---
id: loo-653h
status: open
deps: []
links: []
created: 2026-02-27T15:50:02Z
type: feature
priority: 3
assignee: Michael Barrett
---
# Removed players retain read-only game access

When a player is removed from a game, they currently lose all access (GameMember row deleted). It would be fair to preserve read-only access to the game they participated in.

Approach: Add MemberRole.removed enum value (no DB migration needed — native_enum=False means it's a VARCHAR). Change remove_player route to set role=removed instead of deleting. Add _require_active_member() helper. Update all POST/write routes across ~9 router files (games.py, acts.py, scenes.py, characters.py, oracles.py, session0.py, word_seeds.py, safety_tools.py, world_document.py) to use the new helper. Removed members can view pages but receive 403 on any write action. Show a 'you were removed from this game — read-only access' banner on game_detail.html.

Deferred from loo-ewgh Step 40.

