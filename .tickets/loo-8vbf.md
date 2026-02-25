---
id: loo-8vbf
status: closed
deps: []
links: []
created: 2026-02-25T02:29:44Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:readability]
---
# Inline style attributes scattered throughout templates instead of CSS classes

**Files**: loom/templates/game_detail.html, loom/templates/game_settings.html, loom/templates/games.html, loom/templates/invite.html. Multiple templates use inline style attributes (e.g., style='margin-top:0.5rem;', style='display:inline-block;', style='margin-top:1rem;'). This is scattered and inconsistent — game_settings.html alone has at least 8 inline style declarations. Since base.html already links a static directory, spacing and layout utilities belong in a stylesheet. Inline styles also make it impossible to apply consistent theming. **Suggested Fix**: Create a loom/static/style.css with utility classes and replace inline styles with class attributes.


## Notes

**2026-02-25T02:39:46Z**

Closing: UI polish is explicitly deferred in the development plan. Phase 1 is building functional flows, not a polished UI. CSS architecture is a Phase 2+ concern.
