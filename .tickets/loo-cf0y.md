---
id: loo-cf0y
status: closed
deps: []
links: []
created: 2026-02-25T02:29:13Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:perf]
---
# get_current_user issues a DB lookup on every authenticated request with no caching

**File**: loom/dependencies.py
**Line(s)**: 13-26
**Description**: get_current_user calls db.get(User, user_id) on every single authenticated request. FastAPI dependencies are re-evaluated per request, so every page load incurs a User SELECT against the database, even for endpoints that already load additional game data in the same request.

This is a standard trade-off in web frameworks, but it compounds with the game-scoped endpoints in games.py which also load game members, meaning an authenticated game route performs at minimum two database round-trips before any business logic runs.

**Suggested Fix**: For the stub phase this is acceptable. When real OAuth is wired in (Step 25), consider storing lightweight user data (id, display_name, role) directly in the signed session cookie so the user row does not need to be re-fetched on every request. Alternatively, a request-scoped cache using a FastAPI dependency with a dict stored on the request state would avoid duplicate fetches within a single request context.


## Notes

**2026-02-25T02:39:35Z**

Closing: premature optimization. Per-request user DB lookup is a single indexed SELECT by primary key. With a player cap of 5 per game and dev-only usage, there is nothing to optimize here. Reconsider if real-world load testing reveals it as a bottleneck after Step 25.
