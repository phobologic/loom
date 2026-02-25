---
id: loo-kmm2
status: closed
deps: []
links: []
created: 2026-02-25T04:50:47Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:security]
---
# Jinja2 templates render user content without explicit escaping in some contexts


## Notes

**2026-02-25T04:50:58Z**

**Files**: loom/templates/characters.html (lines 29, 33, 37, 54, 58, 61), loom/templates/world_document.html (line 8), loom/templates/session0_wizard.html (lines 150, 163)
**Description**: Jinja2 auto-escaping is enabled by default for .html templates when using Jinja2Templates, so most `{{ variable }}` expressions are safe. However, two patterns in the new templates merit review:

1. **world_document.html line 8**: The world document content is rendered inside a `<div style='white-space:pre-wrap;'>` using `{{ world_document.content }}`. This is auto-escaped so HTML injection is prevented, but because the content is AI-generated and stored verbatim, if auto-escaping is ever disabled (e.g., the content is marked `|safe` in a future change) this becomes an XSS vector.

2. **characters.html lines 33/37** and **session0_wizard.html line 163**: User-provided `description`, `notes`, and `content` fields are rendered directly. Auto-escaping protects these today, but there is no explicit confirmation that the Jinja2Templates instance is configured with `autoescape=True`.

**Suggested Fix**: Explicitly confirm autoescape is enabled in the shared Jinja2Templates instance in loom/rendering.py:
```python
templates = Jinja2Templates(
    directory=Path(__file__).parent / 'templates',
    autoescape=True,
)
```
FastAPI's default enables autoescaping for .html/.htm/.xml files, but making it explicit documents the intent and protects against future misconfiguration. Never use the `|safe` filter on any user-supplied or AI-generated content.
