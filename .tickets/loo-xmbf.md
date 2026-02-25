---
id: loo-xmbf
status: closed
deps: []
links: []
created: 2026-02-25T02:30:13Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# dev_login POST does not validate that the submitted user_id exists in the database

**File**: loom/routers/auth.py | **Line(s)**: 32-39 | **Description**: The POST /dev/login handler stores whatever integer user_id is submitted directly into the session without checking whether that user exists. A developer (or anyone with access to the dev login page) can log in as a non-existent user ID. get_current_user will then clear the session and redirect to /dev/login on the next request, but the first request that hits a route using get_current_user will still attempt a DB lookup. More importantly, any route that reads user_id from the session without calling get_current_user would operate on a phantom user. | **Suggested Fix**: Look up the User by ID before setting the session, and return a 400/422 if not found.


## Notes

**2026-02-25T02:39:17Z**

Closing: intentionally deferred. Accepting an arbitrary user_id without DB verification is the whole point of the dev login — it lets developers instantly switch between test users. This route is replaced entirely in Step 25.
