---
id: loo-1gab
status: closed
deps: []
links: []
created: 2026-02-25T04:51:51Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:readability]
---
# move_prompt uses a single-element tuple for status check — misleading syntax

**File**: loom/routers/session0.py
**Line(s)**: 1114
**Description**: The status guard is written as 'if target.status not in (PromptStatus.pending,)' — using a single-element tuple. This is syntactically valid but looks like the author intended to add more statuses and left a trailing comma by accident. Every other guard in the same file uses a direct equality check ('!= PromptStatus.active') when there is only one value to compare against.
**Suggested Fix**: Use a direct equality check for consistency: 'if target.status != PromptStatus.pending'. If the intent is to allow additional statuses in the future, add a comment explaining that.

