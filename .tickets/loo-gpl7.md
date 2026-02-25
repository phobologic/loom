---
id: loo-gpl7
status: closed
deps: []
links: []
created: 2026-02-25T02:29:16Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:readability]
---
# Hardcoded error string 'maximum 5 players' in join_game duplicates MAX_GAME_PLAYERS

**File**: loom/routers/games.py, line 191. The error message 'This game is full (maximum 5 players).' embeds the literal 5 rather than referencing MAX_GAME_PLAYERS. If the constant changes, the error message will be stale and misleading. **Suggested Fix**: Replace the literal with an f-string: f'This game is full (maximum {MAX_GAME_PLAYERS} players).'.

