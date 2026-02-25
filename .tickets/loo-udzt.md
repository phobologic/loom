---
id: loo-udzt
status: closed
deps: []
links: [loo-vr9i]
created: 2026-02-25T04:51:12Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# synthesize_prompt and regenerate_synthesis are identical — dead code duplication

**File**: loom/routers/session0.py
**Line(s)**: 258-284, 287-313
**Description**: synthesize_prompt and regenerate_synthesis are byte-for-byte identical in logic. They both call session0_synthesis with the same inputs, set prompt.synthesis and prompt.synthesis_accepted=False, commit, and redirect. The only difference is the URL path (/synthesize vs /regenerate). Having two routes that do exactly the same thing creates maintenance risk — a future change to one will likely miss the other. The initial synthesize route also does not guard against re-synthesis when a synthesis has already been accepted (synthesis_accepted is True and status is complete), potentially overwriting an accepted result.
**Suggested Fix**: Collapse into a single route or have regenerate call the same handler function. Add a guard on synthesize to refuse if prompt.synthesis_accepted is already True.


## Notes

**2026-02-25T04:55:05Z**

Duplicate of loo-vr9i (synthesize_prompt/regenerate_synthesis identical bodies)
