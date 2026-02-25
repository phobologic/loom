---
id: loo-vr9i
status: closed
deps: []
links: [loo-udzt, loo-5mol]
created: 2026-02-25T04:50:28Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:readability]
---
# synthesize_prompt and regenerate_synthesis share identical bodies

**File**: loom/routers/session0.py
**Line(s)**: 901-930 (synthesize_prompt), 933-962 (regenerate_synthesis)
**Description**: The two route handlers are functionally identical — same auth check, same prompt lookup, same synthesis call, same response. Only their docstrings differ. A bug fix in one will not automatically be applied to the other.
**Suggested Fix**: Extract shared body into a private _run_synthesis(prompt, game, db) helper called from both handlers, keeping the two routes as distinct URL endpoints.

