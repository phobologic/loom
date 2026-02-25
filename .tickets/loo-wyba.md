---
id: loo-wyba
status: open
deps: []
links: []
created: 2026-02-25T02:30:04Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# oracle_interpretations property returns empty list on None — hides uninitialized state

**File**: loom/models.py | **Line(s)**: 360-362 | **Description**: The interpretations property returns [] when oracle_interpretations is None. This masks the difference between 'no interpretations generated yet' and 'generated but empty list'. Callers that rely on a non-empty list to decide whether to call the AI stub will silently skip generation if the column was never set. | **Suggested Fix**: Distinguish the two states explicitly: return None (or raise AttributeError) when the column is None, and return the parsed list only when it is a non-null string. Update callers accordingly.

