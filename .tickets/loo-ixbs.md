---
id: loo-ixbs
status: closed
deps: []
links: []
created: 2026-02-25T04:50:56Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# propose_ready_to_play allows duplicate open proposals

**File**: loom/routers/world_document.py, loom/routers/session0.py
**Line(s)**: world_document.py:143-155, session0.py:516-539, 545-572
**Description**: create_world_doc_and_proposal reuses an existing open proposal if one exists. However complete_session0 and propose_ready_to_play are two separate entry points that can each call this function. If an open proposal already exists (e.g., from a previous propose_ready_to_play call), complete_session0 will silently reuse it, potentially changing its proposal_type in-memory or confusing the vote state. The proposal_type field is set only at creation time, so if the open proposal was originally a ready_to_play type and the organizer then calls complete_session0 (world_doc_approval type), a world_doc_approval result is processed under a ready_to_play proposal record. This is a state confusion bug.
**Suggested Fix**: Add a check that the existing open proposal matches the expected proposal_type, or reject the action if a conflicting open proposal exists.

