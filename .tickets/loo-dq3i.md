---
id: loo-dq3i
status: closed
deps: []
links: [loo-h28d]
created: 2026-02-25T02:29:01Z
type: task
priority: 0
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:security]
---
# Dev-only auth routes exposed with no environment guard

**File**: loom/routers/auth.py, loom/main.py | **Line(s)**: auth.py:24-46, main.py:43-44 | **Description**: /dev/login and /dev/logout allow any visitor to authenticate as any seeded user without a password, and are registered unconditionally regardless of the environment setting. In production this allows account takeover by submitting a POST with an arbitrary user_id integer. | **Suggested Fix**: Gate router registration on settings.environment \!= 'production'. Also verify the user exists in the DB before writing user_id to the session inside dev_login.


## Notes

**2026-02-25T02:39:06Z**

Closing: intentionally deferred per the development plan. Step 3 explicitly describes a dev-only auth system designed to make it easy to switch between test users. This is replaced by real OAuth (Google/Discord) in Step 25. The reviewer is correct that this would be critical in production, but it cannot be deployed to production without real auth in place.
