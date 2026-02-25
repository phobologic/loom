---
id: loo-vllm
status: closed
deps: []
links: []
created: 2026-02-25T04:52:00Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# accept_synthesis does not guard against accepting when no synthesis exists

**File**: loom/routers/session0.py
**Line(s)**: 317-343
**Description**: accept_synthesis sets prompt.synthesis_accepted = True and prompt.status = PromptStatus.complete without first checking that prompt.synthesis is not None. If an organizer somehow reaches the accept endpoint without having generated a synthesis first (e.g., via direct HTTP POST, or if the UI allows it when synthesis is None), the prompt will be marked complete with synthesis=None and synthesis_accepted=True. Downstream consumers of the synthesis field (such as _collect_session0_data and generate_world_document) then receive None where they expect a string.
**Suggested Fix**: Add a guard: if prompt.synthesis is None: raise HTTPException(status_code=400, detail='No synthesis to accept')

