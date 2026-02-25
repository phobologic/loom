---
id: loo-57gh
status: closed
deps: []
links: [loo-3zso]
created: 2026-02-25T04:50:49Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:readability]
---
# Confusing threshold expression in view_world_document obscures voting logic

**File**: loom/routers/world_document.py
**Line(s)**: 1422
**Description**: The line 'threshold = game.status != GameStatus.active and total_players / 2 or 0' uses Python's truthy short-circuit evaluation as a conditional expression. This is harder to read than an explicit if/else, and mixing a boolean condition with arithmetic makes the intent unclear at a glance. The voting module already exposes approval_threshold() for exactly this purpose.
**Suggested Fix**: Use approval_threshold() from loom.voting and an explicit conditional: 'threshold = approval_threshold(total_players) if game.status != GameStatus.active else 0'. This also eliminates the implicit duplication of the threshold formula.


## Notes

**2026-02-25T04:55:31Z**

Duplicate of loo-3zso (same threshold short-circuit bug in view_world_document, readability angle)
