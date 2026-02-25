---
id: loo-ddnq
status: open
deps: []
links: []
created: 2026-02-25T02:29:49Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:security]
---
# No input length validation on game name or pitch in create_game route

**File**: loom/routers/games.py | **Line(s)**: 62-63 | **Description**: The create_game handler accepts name and pitch as raw Form strings with no server-side length validation beyond what the DB column enforces (name String(200), pitch Text). An oversized name will cause a DB-level truncation or error rather than a clean 422 response. The pitch field has no upper bound at all. This can be used to store very large text blobs, wasting storage. The HTML maxlength=200 on the name field is a client-side-only control and is trivially bypassed. | **Suggested Fix**: Add server-side length checks: if len(name) > 200: raise HTTPException(422). Consider capping pitch at a reasonable limit (e.g. 2000 chars) both in the model and the route handler.

