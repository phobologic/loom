---
id: loo-5mol
status: closed
deps: []
links: [loo-vr9i]
created: 2026-02-25T04:51:10Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:perf]
---
# synthesize_prompt and regenerate_synthesis are identical — duplicate DB + AI call overhead

**File**: loom/routers/session0.py
**Line(s)**: 206-229 (synthesize_prompt), 231-254 (regenerate_synthesis)
**Description**: The synthesize_prompt and regenerate_synthesis handlers are byte-for-byte identical in logic: both load the full game, check organizer membership, find the prompt, build the inputs list, call session0_synthesis(), set synthesis_accepted=False, commit, and redirect. There is no behavioral difference between them. This means every future change (e.g. adding error handling, caching the synthesis call, rate-limiting) must be applied twice, and any divergence becomes a latent bug.
**Suggested Fix**: Consolidate into a single handler. A query parameter (?regenerate=1) or a common private function called by both routes would eliminate the duplication without changing the URL surface area.
**Importance**: Medium


## Notes

**2026-02-25T04:55:05Z**

Duplicate of loo-vr9i (same duplication, perf angle; loo-vr9i has the clearest suggested fix)
