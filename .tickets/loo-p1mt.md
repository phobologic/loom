---
id: loo-p1mt
status: closed
deps: []
links: []
created: 2026-02-25T04:51:09Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:security]
---
# Race condition (TOCTOU) still present in vote deduplication check


## Notes

**2026-02-25T04:51:18Z**

**File**: loom/routers/world_document.py
**Line(s)**: 228-240
**Description**: cast_vote checks for an existing vote using an in-memory scan of the already-loaded proposal.votes collection, then inserts a new Vote if none is found. Under concurrent requests from the same user, two requests could both pass the existing-vote check before either commits, resulting in two votes from the same user on the same proposal. The database has a UniqueConstraint('proposal_id', 'voter_id') on the votes table, so the second commit would fail with an IntegrityError, but this error is not caught — it would surface as an unhandled 500 to the user rather than a friendly 409.

Note: The games.py join_game endpoint was improved in this diff to re-query the count before inserting (narrowing the TOCTOU window). The same pattern should be applied to vote creation.

**Suggested Fix**: Either:
1. Catch IntegrityError around the commit and return a 409, or
2. Use an INSERT ... ON CONFLICT DO NOTHING with a follow-up SELECT, or
3. Re-query the database for an existing vote immediately before inserting rather than relying on the in-memory collection:
```python
existing_check = await db.execute(
    select(Vote).where(Vote.proposal_id == proposal_id, Vote.voter_id == current_user.id)
)
if existing_check.scalar_one_or_none() is not None:
    raise HTTPException(status_code=409, detail='You have already voted on this proposal')
```
