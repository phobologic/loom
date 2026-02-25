---
id: loo-1ft4
status: closed
deps: []
links: []
created: 2026-02-25T04:51:15Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:readability]
---
# format_safety_tools_context uses untyped list parameter — inconsistent with project typing conventions

**File**: loom/ai/stubs.py
**Line(s)**: 29
**Description**: format_safety_tools_context is typed as 'tools: list' (bare list with no element type). The project uses modern generic syntax throughout (list[str], list[Session0Prompt], etc.). Using a bare list loses IDE support, static analysis, and documentation of what the caller should pass. The docstring partially compensates by describing the expected shape, but the type annotation itself should carry that information.
**Suggested Fix**: Import a Protocol or use the concrete model type. At minimum, use Sequence[Any] with a comment, or better: define a narrow Protocol with the two attributes the function actually accesses (.kind.value and .description) and use that as the parameter type.

