---
id: loo-tzkh
status: open
deps: [loo-9hbi]
links: []
created: 2026-02-26T20:55:52Z
type: chore
priority: 3
assignee: Michael Barrett
---
# Move cast_vote endpoint out of world_document.py into a dedicated proposals router

The cast_vote POST handler (and associated helpers: _resolve_tension_proposal, _create_tension_adjustment_proposal, _load_game_for_voting) lives in world_document.py for historical reasons — world doc approval was the first vote surface built, and later proposal types (act, scene, beat, tension) accreted into the same file. The file is now doing double duty as both the world-document feature module and the system-wide voting engine. Refactor: extract to a dedicated loom/routers/proposals.py (or voting.py), leaving world_document.py with only the world-doc-specific GET/POST routes. No behavior changes.

