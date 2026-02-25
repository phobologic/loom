---
id: loo-7hys
status: closed
deps: []
links: []
created: 2026-02-25T04:50:56Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:perf]
---
# world_document.py _load_game_for_voting issues two selectinload paths for proposals

**File**: loom/routers/world_document.py
**Line(s)**: 68-77
**Description**: _load_game_for_voting specifies two separate selectinload chains that both start from Game.proposals:
  selectinload(Game.proposals).selectinload(VoteProposal.votes).selectinload(Vote.voter)
  selectinload(Game.proposals).selectinload(VoteProposal.proposed_by)
SQLAlchemy will issue separate SELECT statements for each chain. This means proposals are loaded, then votes+voters are loaded in one query, then proposed_by users are loaded in another. Combining them under a single contains_eager or using a joined load for the shallow proposed_by relationship would reduce the number of round-trips by one.
**Suggested Fix**: Use a single selectinload(Game.proposals).options(selectinload(VoteProposal.votes).selectinload(Vote.voter), selectinload(VoteProposal.proposed_by)) to keep the structure explicit while reducing the number of emitted queries.
**Importance**: Low

