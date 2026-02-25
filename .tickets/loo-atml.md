---
id: loo-atml
status: closed
deps: []
links: []
created: 2026-02-25T04:50:37Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:readability]
---
# _load_game_with_members duplicated across routers — should reuse shared helper

**File**: loom/routers/safety_tools.py (line 506-510), loom/routers/games.py (pause_game, resume_game, archive_game inline selects)
**Line(s)**: safety_tools.py:506-510, games.py:383-386, games.py:410-413, games.py:438-441
**Description**: _load_game_with_members is defined locally in safety_tools.py, and the same three-line select+options pattern is inlined three more times in the new games.py endpoints (pause, resume, archive). All four are structurally identical. Having the same query in multiple places means adding a new eager-load (e.g. selectinload Game.session0_prompts) must be done everywhere.
**Suggested Fix**: Define _load_game_with_members once in a shared helper module and import it wherever needed.

