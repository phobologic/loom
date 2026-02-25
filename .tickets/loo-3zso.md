---
id: loo-3zso
status: closed
deps: []
links: [loo-57gh]
created: 2026-02-25T04:50:36Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# threshold variable in view_world_document uses incorrect short-circuit operator


## Notes

**2026-02-25T04:50:48Z**

File: loom/routers/world_document.py Line 186. The threshold line uses Python short-circuit boolean: 'threshold = game.status \!= GameStatus.active and total_players / 2 or 0'. When the game is active, the expression evaluates to False (a boolean), not 0 (an integer). When not active, total_players / 2 is a float. The approval_threshold function already exists in loom/voting.py and should be reused here. Fix: 'threshold = approval_threshold(total_players) if game.status \!= GameStatus.active else 0'
