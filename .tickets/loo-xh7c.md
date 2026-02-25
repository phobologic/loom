---
id: loo-xh7c
status: open
deps: []
links: []
created: 2026-02-25T02:30:19Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:readability]
---
# ActStatus and SceneStatus are identical enums — consider sharing or consolidating

**File**: loom/models.py lines 47-60. ActStatus and SceneStatus both define the same three values: proposed, active, complete. They exist as separate types to give the type checker distinct column types — which is intentional and correct. However, there is no comment explaining why these are not shared. A future developer may see the duplication and collapse them, breaking the type distinction. **Suggested Fix**: Add a brief comment above one of the enums noting the intentional separation: '# Distinct from ActStatus even though values match, so type checking catches misuse.'.

