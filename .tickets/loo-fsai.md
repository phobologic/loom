---
id: loo-fsai
status: closed
deps: []
links: []
created: 2026-02-25T04:50:49Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:perf]
---
# game_detail loads acts+scenes eagerly but then re-sorts them in Python

**File**: loom/routers/games.py
**Line(s)**: 108-110
**Description**: The game_detail handler eagerly loads acts and their scenes from the DB, then sorts both collections in Python after the fact (acts = sorted(...); act.scenes.sort(...)). The DB query does not specify an ORDER BY, so the DB returns rows in an undefined order and Python re-sorts the entire result set on every page view.
**Suggested Fix**: Add order_by to the selectinload options or to the Game.acts relationship definition (as is already done for session0_prompts and safety_tools in models.py), so the database returns rows pre-sorted and the Python sort calls can be removed entirely.
**Importance**: Low

