---
id: loo-h28d
status: closed
deps: []
links: [loo-dq3i]
created: 2026-02-25T02:28:45Z
type: task
priority: 0
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# dev auth routes not guarded by environment check

**File**: loom/routers/auth.py
**Line(s)**: 24-46
**Description**: The /dev/login, /dev/login (POST), and /dev/logout routes are mounted unconditionally. There is no guard on the environment setting (e.g. `settings.environment != 'local'`). If this application is ever deployed with the default or a misconfigured environment value, any visitor can log in as any seeded user with zero credentials. This is a critical security flaw because the only protection is a convention — the developer must remember to configure the environment — not an enforced code path.
**Suggested Fix**: Add an early-exit guard in each dev route (or in a router-level dependency) that raises HTTP 404 or 403 when `settings.environment != 'local'`. Alternatively, conditionally include the auth router in main.py only when the environment check passes.


## Notes

**2026-02-25T02:32:39Z**

Duplicate of loo-dq3i
