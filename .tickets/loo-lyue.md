---
id: loo-lyue
status: closed
deps: []
links: [loo-09qa]
created: 2026-02-25T02:28:46Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:readability]
---
# Duplicated Jinja2Templates instantiation across all three routers

**File**: loom/routers/auth.py (line 19), loom/routers/games.py (line 27), loom/routers/pages.py (line 5)
**Description**: All three router modules independently instantiate `Jinja2Templates(directory='loom/templates')`. This is repeated boilerplate — if the template directory path ever changes, it must be updated in three places. A single shared `templates` instance should be defined once (e.g., in `loom/dependencies.py` or a new `loom/templates_config.py`) and imported by each router.
**Suggested Fix**: Define `templates = Jinja2Templates(directory='loom/templates')` once in a shared module and import it in each router.

