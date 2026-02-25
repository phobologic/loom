---
id: loo-w2vt
status: closed
deps: []
links: []
created: 2026-02-25T02:29:27Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# invite_token collision not handled — secrets.token_urlsafe could theoretically collide on unique constraint

**File**: loom/routers/games.py | **Line(s)**: 72, 291 | **Description**: Both create_game and regenerate_invite assign a new token directly without catching the IntegrityError that would occur on a (extremely unlikely but possible) collision against the unique constraint on invite_token. The database would surface an unhandled 500. With token_urlsafe(32) the probability is negligible but the code should be defensive for correctness. | **Suggested Fix**: Either retry on IntegrityError, or accept the theoretical risk and document it.


## Notes

**2026-02-25T02:39:35Z**

Closing: negligible risk. secrets.token_urlsafe(32) produces 256 bits of entropy. The probability of a collision is ~1/2^192 — lower than a hardware bit-flip. Not worth handling.
