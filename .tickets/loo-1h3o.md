---
id: loo-1h3o
status: closed
deps: []
links: []
created: 2026-02-25T04:52:07Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# archive_game allows archiving a setup-phase game

**File**: loom/routers/games.py
**Line(s)**: 350-378
**Description**: archive_game only prevents archiving an already-archived game. It permits archiving games in setup or paused status. pause_game and resume_game are correctly constrained (only active -> paused, only paused -> active), but archive_game accepts any non-archived status, including setup. This means a game can be archived before Session 0 is even started, bypassing the normal lifecycle. Whether this is intentional is not documented, and tests do not cover this case.
**Suggested Fix**: If archiving a setup game is unintended, add: if game.status == GameStatus.setup: raise HTTPException(status_code=403, detail='Cannot archive a game that has not started'). Otherwise, document the intent explicitly.

