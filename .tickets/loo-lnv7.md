---
id: loo-lnv7
status: closed
deps: []
links: []
created: 2026-02-25T04:50:38Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:security]
---
# Custom prompt question has no length or content validation

**File**: loom/routers/session0.py
**Line(s)**: 415-437
**Description**: The add_custom_prompt endpoint accepts a question string from a form and stores it after a strip(). There is no maximum length check and no guard against an empty-after-strip value. A malicious organizer could insert an extremely long prompt question, which is then stored in the DB, rendered in the sidebar (truncated client-side via the Jinja truncate filter, but fully stored), and potentially passed to the AI synthesis functions.
**Suggested Fix**: Validate that question is non-empty after stripping and impose a reasonable max length (e.g., 500 characters):
```python
question = question.strip()
if not question:
    raise HTTPException(status_code=422, detail='Question cannot be empty')
if len(question) > 500:
    raise HTTPException(status_code=422, detail='Question cannot exceed 500 characters')
```

