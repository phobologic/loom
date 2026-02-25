---
id: loo-gmg6
status: closed
deps: []
links: []
created: 2026-02-25T04:50:36Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:perf]
---
# In-memory linear scans used to look up prompt/character by id instead of DB primary key lookup

**File**: loom/routers/session0.py, loom/routers/characters.py
**Line(s)**: session0.py:222, 249, 275, 304, 336, 366, 400, 432 (next(...) over game.session0_prompts); characters.py:34-37 (_find_character)
**Description**: After eagerly loading the full prompt list (or character list), every handler then uses a linear Python scan — next(p for p in game.session0_prompts if p.id == prompt_id) — to locate a single row by primary key. The database index on the id column is bypassed entirely. The same pattern appears in _find_character() for characters. While the collections are small today, this pattern scales poorly if prompt/character counts grow and avoids using the DB's O(1) primary-key path.
**Suggested Fix**: Use db.get(Session0Prompt, prompt_id) for a direct identity-map / primary-key lookup, or issue a targeted SELECT WHERE id = :id with a WHERE game_id = :game_id guard. This removes the need to load the entire collection just to find one row.
**Importance**: Medium

