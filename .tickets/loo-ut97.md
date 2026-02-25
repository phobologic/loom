---
id: loo-ut97
status: open
deps: []
links: [loo-5wvn]
created: 2026-02-25T02:29:52Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# TestFullGameFlow creates a GameMember but never adds it to the session

**File**: tests/test_models.py | **Line(s)**: 374 | **Description**: GameMember(game_id=game.id, user_id=user.id, role=MemberRole.organizer) is instantiated but the result is not assigned and db_session.add() is never called on it. The membership record is silently dropped. This means the test does not actually verify that the cascade handles a game that has members, undermining the stated intent of test_full_flow_and_cascade. | **Suggested Fix**: Assign the result and add it: member = GameMember(...); db_session.add(member); await db_session.flush()

