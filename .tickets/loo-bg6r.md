---
id: loo-bg6r
status: closed
deps: []
links: [loo-5834]
created: 2026-02-25T04:50:31Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:security]
---
# Voting threshold logic allows zero-player auto-approval

**File**: loom/voting.py (lines 7-12), loom/routers/world_document.py (line 133)
**Description**: approval_threshold(0) returns 0.0, and is_approved(0, 0) returns False (0 > 0 is False), which is fine. However is_approved(1, 0) returns True (1 > 0), meaning if a game somehow has zero members but a vote is cast, it auto-approves. More practically, if total_players is ever computed from an incomplete relationship load and returns 0, any single yes vote immediately transitions the game to active status. There is no guard ensuring total_players >= 1 before the approval check.
**Suggested Fix**: Add a guard in is_approved (or at call sites) to require at least one player:
```python
def is_approved(yes_count: int, total_players: int) -> bool:
    if total_players < 1:
        return False
    return yes_count > approval_threshold(total_players)
```


## Notes

**2026-02-25T04:55:54Z**

Duplicate of loo-5834 (same is_approved zero-player auto-approval bug in voting.py)
