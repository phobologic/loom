---
id: loo-pfg9
status: closed
deps: []
links: []
created: 2026-02-25T04:50:44Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:security]
---
# move_prompt direction input not validated against allowlist

**File**: loom/routers/session0.py
**Line(s)**: 441-476
**Description**: The direction form parameter is accepted as a raw string and compared with == 'up' / == 'down'. Any value other than those two silently results in a no-op. While there is no security impact today (the parameter only controls a swap operation between in-memory objects), accepting unvalidated enum-like inputs is a bad pattern that should be corrected for consistency and to prevent confusion if the logic is later extended.
**Suggested Fix**: Reject unexpected values explicitly:
```python
if direction not in ('up', 'down'):
    raise HTTPException(status_code=422, detail="direction must be 'up' or 'down'")
```

