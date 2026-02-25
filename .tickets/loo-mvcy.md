---
id: loo-mvcy
status: closed
deps: []
links: []
created: 2026-02-25T04:51:31Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:readability]
---
# session0.py imports create_world_doc_and_proposal from world_document router — creates tight cross-router coupling

**File**: loom/routers/session0.py
**Line(s)**: 670
**Description**: session0.py imports create_world_doc_and_proposal and _load_game_for_voting directly from loom.routers.world_document. Routers importing from other routers creates a coupling that makes the dependency graph harder to reason about: changing world_document.py can silently break session0.py, and the shared functions are buried inside a router module rather than in a clearly shared service layer.
**Suggested Fix**: Move create_world_doc_and_proposal and _load_game_for_voting to a dedicated service module (e.g. loom/services/world_document.py or loom/session0_service.py) so both routers import from a neutral shared location. This makes the dependency direction explicit and the shared API surface discoverable.

