---
id: loo-kicp
status: closed
deps: []
links: [loo-pdma]
created: 2026-02-25T02:29:07Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:readability]
---
# Repeated game-fetch-then-membership-check pattern has no shared helper

**File**: loom/routers/games.py — Lines 90-101, 210-219, 243-252, 278-289, 304-313. Five route handlers each repeat: (1) query Game with selectinload(Game.members), (2) 404 if not found, (3) _find_membership + 403 if not a member. The _find_membership helper was correctly extracted but the surrounding scaffold was not. A shared coroutine like _get_game_or_raise(game_id, user, db, require_organizer=False) would centralize this, making access-control changes a single-point edit. **Suggested Fix**: Extract a shared coroutine that performs the full fetch-and-authorize flow and raises HTTPException, replacing the five repeated blocks.


## Notes

**2026-02-25T02:32:54Z**

Duplicate of loo-pdma
