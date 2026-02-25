---
id: loo-gr0t
status: open
deps: []
links: []
created: 2026-02-25T02:29:49Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:readability]
---
# game_settings.html duplicates all settings display logic for organizer vs player view

**File**: loom/templates/game_settings.html lines 15-140. The template has two full branches — an editable form for the organizer (lines 16-89) and a read-only display list for players (lines 93-139). Every setting is listed twice, once in each branch. When a new setting is added, both branches must be updated in sync. **Suggested Fix**: Use a single read-only display (the dl/dd block) visible to all, and conditionally show only the form inputs for organizers. Alternatively, use a Jinja2 macro to avoid repeating each setting's label and value.

