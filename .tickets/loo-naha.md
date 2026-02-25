---
id: loo-naha
status: closed
deps: []
links: []
created: 2026-02-25T04:50:05Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:security]
---
# No length cap on user-supplied free-text fields (Session 0 responses, safety tools, voting suggestions)


## Notes

**2026-02-25T04:50:13Z**

**Files**: loom/routers/session0.py (lines 216-220), loom/routers/safety_tools.py (lines 96-100), loom/routers/world_document.py (lines 218-225)
**Description**: Several POST handlers accept arbitrary-length text from users with no server-side length limit enforced before writing to the database. Specifically:
- session0.py respond_to_prompt: `content` form field (Session0Response.content) has no max-length check.
- safety_tools.py add_safety_tool: `description` field only validates non-empty; no upper bound.
- world_document.py cast_vote: `suggestion` field has no length limit.

While the database column is TEXT (unbounded), accepting very large payloads can cause: memory pressure during request processing, denial-of-service via repeated large submissions, and unexpectedly large AI synthesis inputs when all responses are concatenated in synthesize_prompt.

**Suggested Fix**: Add server-side length validation for all free-text inputs, e.g.:
```python
MAX_RESPONSE_LEN = 2000
if len(content) > MAX_RESPONSE_LEN:
    raise HTTPException(status_code=422, detail=f"Response cannot exceed {MAX_RESPONSE_LEN} characters")
```
Also consider adding `maxlength` attributes to the corresponding HTML textareas for client-side hints.
