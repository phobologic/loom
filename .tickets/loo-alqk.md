---
id: loo-alqk
status: closed
deps: []
links: []
created: 2026-02-25T04:50:19Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# _load_game_with_session0 returns None but callers assume Game

**File**: loom/routers/session0.py
**Line(s)**: 82-94
**Description**: _load_game_with_session0 is annotated as returning Game but actually returns Game | None (result.scalar_one_or_none()). Every call site does a None check, which works in practice, but the wrong return type annotation means type checkers will not flag any future call site that omits the None check. The annotation should be Game | None to match the implementation.
**Suggested Fix**: Change the return type annotation from Game to Game | None.

