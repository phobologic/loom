---
id: loo-mz3j
status: closed
deps: []
links: []
created: 2026-02-25T02:28:48Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:perf]
---
# len(game.members) called twice in invite_landing and join_game

**File**: loom/routers/games.py
**Line(s)**: 148-150, 181
**Description**: In invite_landing, len(game.members) is evaluated twice to compute both member_count and is_full. In join_game, len(game.members) is evaluated again for the cap check after already iterating the list with _find_membership. Each call re-evaluates the length on an already-materialized list, which is harmless today but is an unnecessary redundancy.

**Suggested Fix**: Compute the count once and reuse it:

    member_count = len(game.members)
    ...
    'member_count': member_count,
    'is_full': member_count >= MAX_GAME_PLAYERS,


## Notes

**2026-02-25T02:39:47Z**

Closing: micro-optimization with no meaningful impact. len() on an in-memory list of ≤5 items is negligible. The clarity of reading len(game.members) twice is better than caching it in a local variable.
