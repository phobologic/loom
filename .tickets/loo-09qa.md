---
id: loo-09qa
status: closed
deps: []
links: [loo-lyue]
created: 2026-02-25T02:29:20Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:perf]
---
# Jinja2Templates instantiated once per router module, not a shared singleton

**File**: loom/routers/auth.py (line 19), loom/routers/games.py (line 27), loom/routers/pages.py (line 5)
**Line(s)**: auth.py:19, games.py:27, pages.py:5
**Description**: Each router module creates its own Jinja2Templates instance pointing at the same directory. While Jinja2Templates does cache compiled templates internally per instance, having three separate instances means three separate template caches and three separate FileSystemLoader objects, each of which independently reads and compiles templates from disk on first use.

**Suggested Fix**: Create a single shared Templates instance in a central location (e.g., loom/templates_config.py or loom/main.py) and import it in each router:

    # loom/templating.py
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory='loom/templates')

Each router then imports and reuses the same object, sharing one compiled-template cache.


## Notes

**2026-02-25T02:32:45Z**

Duplicate of loo-lyue
