---
id: loo-b9nt
status: closed
deps: []
links: []
created: 2026-02-25T04:50:22Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# session0_index silently promotes first_pending prompt on stale return visit


## Notes

**2026-02-25T04:50:32Z**

**File**: loom/routers/session0.py
**Line(s)**: 131-148
**Description**: When a returning visitor hits /session0 and there is no active prompt (all were previously completed/skipped), the code quietly sets the first pending prompt to active and commits. This is not idempotent — a network retry, browser refresh, or race condition between two tabs could activate a prompt that was intentionally left pending. More subtly, this code path runs even after a wizard has been fully completed (all_done is True), so a completed game can be put back into an intermediate state.

The adjacent comment says "Handles return visit after all were completed", but if all prompts are done there are no pending ones, so first_pending will be None and the code falls through to the else branch (redirect to last prompt). However, if some prompts were skipped and others pending, this silently reactivates them.

**Suggested Fix**: The promotion of a pending prompt to active should only happen at the explicit direction of the organizer (e.g., via a dedicated UI action), not as a side-effect of a GET request. The index redirect should show the current state without mutating it, or at most redirect to the first non-terminal prompt without changing its status.
