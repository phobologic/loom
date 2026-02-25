---
id: loo-gm7b
status: closed
deps: []
links: [loo-yxpz]
created: 2026-02-25T04:51:26Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# _find_membership duplicated across four router modules

**File**: loom/routers/characters.py:21, loom/routers/safety_tools.py:21, loom/routers/session0.py:55, loom/routers/world_document.py:43
**Line(s)**: (see above)
**Description**: The _find_membership helper function is defined identically in characters.py, safety_tools.py, session0.py, and world_document.py. Any future change to the lookup logic (e.g., adding soft-deleted members) must be applied in all four places. This is a DRY violation that is easy to miss during maintenance.
**Suggested Fix**: Move _find_membership to loom/dependencies.py or a new loom/routers/_common.py and import it in each router.


## Notes

**2026-02-25T04:55:13Z**

Duplicate of loo-yxpz (same _find_membership duplication, logic angle)
