---
id: loo-foq7
status: open
deps: []
links: []
created: 2026-02-25T02:29:12Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:readability]
---
# Hardcoded magic number 5 in game_detail.html duplicates MAX_GAME_PLAYERS constant

**File**: loom/templates/game_detail.html, line 16. The template renders 'Members ({{ members | length }}/5)' with 5 as a literal. The constant MAX_GAME_PLAYERS=5 already exists in loom/routers/games.py. If the cap changes, this display text will silently be wrong. **Suggested Fix**: Pass MAX_GAME_PLAYERS into the template context from the game_detail route handler (alongside 'members') and reference it in the template as '{{ members | length }}/{{ max_players }}'.

