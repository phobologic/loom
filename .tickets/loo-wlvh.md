---
id: loo-wlvh
status: closed
deps: []
links: []
created: 2026-02-25T04:51:03Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# move_prompt allows swapping a pending prompt with an active or complete prompt

**File**: loom/routers/session0.py
**Line(s)**: 430-455
**Description**: move_prompt only validates that the target prompt being moved has a pending status. It does not check the status of the neighbor prompt that will receive the swapped order. This means a pending prompt can be swapped ahead of (or behind) an active or complete prompt. If the active prompt is at order=3 and a pending prompt at order=4 is moved up, the active prompt now has order=4 and the pending one has order=3 — the wizard ordering is now inconsistent with the status timeline that _advance_wizard relies on.
**Suggested Fix**: Also validate that the neighbor prompt is pending before performing the swap, or restrict reordering to only the pending tail of the sequence.

