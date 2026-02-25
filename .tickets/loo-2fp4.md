---
id: loo-2fp4
status: closed
deps: []
links: []
created: 2026-02-25T04:50:42Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:perf]
---
# format_safety_tools_context iterates tools list twice (once for lines, once for veils)

**File**: loom/ai/stubs.py
**Line(s)**: 37-38
**Description**: format_safety_tools_context filters the tools list twice with separate list comprehensions — once for lines and once for veils. For a safety tools list that is expected to be small (typically <20 items) this has no practical impact, but it is a minor inefficiency that can be resolved with a single pass.
**Suggested Fix**: Partition in one pass using a collections.defaultdict or a single loop:

lines, veils = [], []
for t in tools:
    (lines if t.kind.value == 'line' else veils).append(t)

**Importance**: Low

