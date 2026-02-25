---
id: loo-5wvn
status: closed
deps: []
links: [loo-ut97]
created: 2026-02-25T02:30:07Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:readability]
---
# TestFullGameFlow: GameMember created but never added to session — silent no-op

**File**: tests/test_models.py line 374. The test constructs 'GameMember(game_id=game.id, user_id=user.id, role=MemberRole.organizer)' but never calls db_session.add() on it. The object is silently discarded. The test still passes because cascade deletion is tested at the game level, not the member level — but the stated intent of 'Build the full hierarchy' is not fulfilled. **Suggested Fix**: Add 'db_session.add(member)' and 'await db_session.flush()' after constructing the GameMember, and capture it in a variable: 'member = GameMember(...); db_session.add(member); await db_session.flush()'. Optionally add an assertion that the member is also deleted when the game is deleted.


## Notes

**2026-02-25T02:33:04Z**

Duplicate of loo-ut97
