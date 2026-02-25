---
id: loo-tbmo
status: closed
deps: []
links: []
created: 2026-02-25T04:50:28Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:perf]
---
# Full game reload on every synthesize/regenerate/accept/skip handler

**File**: loom/routers/session0.py
**Line(s)**: 208-215, 241-248, 270-278, 300-308, 330-338, 363-371, 396-404, 426-434
**Description**: Every mutating POST endpoint in session0.py calls _load_game_with_session0(), which issues a SELECT with three levels of eager loading (game -> session0_prompts -> responses -> user). Most of these handlers only need to locate and mutate a single Session0Prompt row. Loading all prompts, all responses, and all response users for the purpose of finding one prompt and updating its status is wasteful — it transfers unnecessary data over the DB connection and inflates SQLAlchemy's identity map on every write.
**Suggested Fix**: For handlers that only update a single prompt (synthesize, regenerate, accept, skip, mark-done, respond), load the prompt directly by primary key or with a targeted SELECT joining only what is needed. For example, the synthesize handler only needs game.pitch and the prompt's responses; it does not need the rest of the prompts or the user objects attached to responses.
**Importance**: Medium

