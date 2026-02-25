---
id: loo-4ur6
status: closed
deps: []
links: []
created: 2026-02-25T04:51:44Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# cast_vote does not check proposal game_id matches route game_id

**File**: loom/routers/world_document.py
**Line(s)**: 213-263
**Description**: cast_vote loads the game and then finds the proposal by searching game.proposals (which are proposals for that game). However, the route URL includes both game_id and proposal_id. The lookup 'next((p for p in game.proposals if p.id == proposal_id), None)' is scoped to the game's proposals, so cross-game voting is not possible. This is correct, but worth noting that the game_id in the URL is what constrains the search — if game.proposals were accidentally loaded without filtering by game, this would be a IDOR vulnerability. The current implementation is safe, but the game_id path parameter in the URL (/games/{game_id}/proposals/{proposal_id}/vote) is slightly misleading since game_id only determines which game's proposals are searched. Consider documenting this or adding an explicit assertion that proposal.game_id == game_id for defense in depth.
**Suggested Fix**: Add an explicit check: if proposal.game_id != game_id: raise HTTPException(status_code=404)

