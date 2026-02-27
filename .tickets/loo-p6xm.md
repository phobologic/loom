---
id: loo-p6xm
status: closed
deps: []
links: []
created: 2026-02-25T05:06:42Z
type: epic
priority: 3
assignee: Michael Barrett
---
# Pre-production Cleanup

Code quality, deduplication, performance, and minor validation improvements deferred from the Phase 1 code review (loo-qkrm). Address between Step 22 and Step 25 (Real Auth).

## Duplication
- loo-yxpz / loo-nqdj / loo-gm7b: _find_membership duplicated across 4 routers
- loo-vr9i / loo-udzt / loo-5mol: synthesize_prompt and regenerate_synthesis identical bodies
- loo-mvcy: session0 router imports directly from world_document router
- loo-atml: _load_game_with_members duplicated across routers
- loo-g5gm: test helpers duplicated across test modules

## Performance
- loo-gmg6: O(n) in-memory scans instead of PK lookups
- loo-t13y: double DB round-trip on first session0 visit
- loo-tbmo: full game reload on every mutating session0 POST
- loo-siku: divergent yes_count paths in create_world_doc_and_proposal
- loo-fsai: game_detail sorts in Python instead of ORDER BY
- loo-7hys: two selectinload chains for proposals in world_document
- loo-2fp4: format_safety_tools_context iterates tools list twice

## Minor Validation
- loo-lnv7: custom prompt question has no length/content validation
- loo-pfg9: move_prompt direction not validated against allowlist
- loo-1eu3: respond_to_prompt allows empty content
- loo-1h3o: archive_game permits setup-status games

## Readability / Low
- loo-opum: _load_game_with_session0 missing docstring
- loo-8esb: identity-map comment needs more context
- loo-1ft4: format_safety_tools_context uses bare list type
- loo-gg6r: _find_character/_my_character inconsistent style
- loo-1gab: move_prompt uses single-element tuple for status check
- loo-6jti: _AuthRedirect private prefix contradicts cross-module import

