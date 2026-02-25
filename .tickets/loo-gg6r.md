---
id: loo-gg6r
status: closed
deps: []
links: []
created: 2026-02-25T04:51:08Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:readability]
---
# _find_character and _my_character helpers lack type annotations on the loop variable

**File**: loom/routers/characters.py
**Line(s)**: 55-68
**Description**: _find_character and _my_character iterate over game.characters but the loop variable (c) is untyped. While SQLAlchemy's mapped_column gives the collection type, explicitly annotating the helpers' return types is all that is present. Minor, but the similar helper _find_membership in the same file uses the same style consistently, so this is not a blocking inconsistency. The bigger readability concern is that all three helpers use a for-loop search over a loaded collection in a pattern that could be replaced by next() with a generator expression, matching the style used inline elsewhere in the same file (e.g. 'next((p for p in ...), None)').
**Suggested Fix**: Use next() with a generator expression for consistency with the rest of the file: 'return next((c for c in game.characters if c.id == char_id), None)'

