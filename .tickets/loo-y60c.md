---
id: loo-y60c
status: closed
deps: []
links: []
created: 2026-02-25T02:29:05Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:perf]
---
# N+1 query risk: _seed_dev_users issues one SELECT per user

**File**: loom/main.py
**Line(s)**: 20-27
**Description**: _seed_dev_users executes a separate SELECT for each name in _DEV_USERS inside a loop. With 3 dev users this is 3 round-trips to the database at startup. This is a classic N+1 pattern.

Although the startup cost is negligible with 3 users, the pattern will not scale if the list grows and is worth correcting as a habit.

**Suggested Fix**: Fetch all existing names in a single query, then insert only the missing ones:

    result = await session.execute(select(User.display_name).where(User.display_name.in_(_DEV_USERS)))
    existing = {row[0] for row in result}
    for name in _DEV_USERS:
        if name not in existing:
            session.add(User(display_name=name))
    await session.commit()


## Notes

**2026-02-25T02:41:40Z**

Closing: not a real concern. _seed_dev_users is dev-only startup code that seeds exactly 4 hardcoded test users. It runs once at startup, never in a hot path, and will never grow. Refactoring it to a single query would add complexity with zero practical benefit.
