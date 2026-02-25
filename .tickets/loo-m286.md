---
id: loo-m286
status: closed
deps: []
links: []
created: 2026-02-25T02:28:42Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:perf]
---
# Repeated linear scan through game.members in _find_membership

**File**: loom/routers/games.py
**Line(s)**: 34-39, called at 99, 139, 177, 217, 250, 285, 311
**Description**: _find_membership iterates all members in Python with a for-loop on every route handler that needs authorization. Since game.members is already eager-loaded (selectinload), this is O(n) in Python rather than a filtered SQL query, and it is called once per request on every game-scoped endpoint.

With a MAX_GAME_PLAYERS cap of 5 the constant factor is trivially small today, but the pattern is worth noting in case the cap is raised or the helper is reused for other collections without a cap.

**Suggested Fix**: Build a dict keyed by user_id once after loading, or convert the loaded list to a set lookup. Alternatively, simply use next() with a generator expression to avoid a named helper entirely:

    current_member = next((m for m in game.members if m.user_id == current_user.id), None)

This keeps the same O(n) complexity but removes the need for a separate function.


## Notes

**2026-02-25T02:39:47Z**

Closing: not worth fixing. The player cap is 5. A linear scan over at most 5 members is O(1) in practice. Converting to a dict would add complexity with zero measurable benefit.
