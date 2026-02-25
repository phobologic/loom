---
id: loo-siku
status: closed
deps: []
links: []
created: 2026-02-25T04:51:19Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:perf]
---
# create_world_doc_and_proposal computes yes_count with divergent logic paths that could desync

**File**: loom/routers/world_document.py
**Line(s)**: 139-155
**Description**: create_world_doc_and_proposal uses two different code paths to compute yes_count depending on whether the proposal is brand-new (is_new_proposal=True) or reused (is_new_proposal=False). For the new-proposal case it hardcodes yes_count as 1-if-added_yes-else-0, silently ignoring any votes that might already exist on the newly flushed proposal (impossible today but fragile). For the reused-proposal case it iterates proposal.votes in memory. These divergent paths increase cognitive complexity and make it harder to verify correctness during code review or refactoring.

Additionally, the yes_count computation for the reused path iterates proposal.votes twice when added_yes is True (once in the sum(), then +1). A single pass would be cleaner.

**Suggested Fix**: Unify the two paths after the flush by always computing yes_count from the in-memory votes list, ensuring the newly added Vote has been appended to proposal.votes before the count. Alternatively, after flush, issue a SELECT COUNT(*) WHERE choice='yes' to get an authoritative count from the database.
**Importance**: Medium

