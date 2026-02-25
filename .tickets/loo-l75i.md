---
id: loo-l75i
status: closed
deps: []
links: []
created: 2026-02-25T02:30:21Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# player cap checked against game.members length which may be stale if loaded without selectinload

**File**: loom/routers/games.py | **Line(s)**: 181 | **Description**: join_game checks len(game.members) >= MAX_GAME_PLAYERS. The members relationship is eagerly loaded via selectinload on line 165, which is correct. However, there is a TOCTOU window: two concurrent POST /invite/{token} requests for the same token can both read len(game.members) == 4, both pass the cap check, and both insert a GameMember, resulting in 6 members. The unique constraint on (game_id, user_id) only prevents the same user joining twice, not two different users joining simultaneously. | **Suggested Fix**: Use a SELECT COUNT with FOR UPDATE or a serializable transaction around the member count check and insert to prevent the race.

