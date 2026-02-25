---
id: loo-vjay
status: open
deps: []
links: []
created: 2026-02-25T02:29:13Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# invite_landing returns 200 for invalid token instead of 404

**File**: loom/routers/games.py | **Line(s)**: 130-135 | **Description**: When the invite token is not found, invite_landing (GET /invite/{token}) returns a TemplateResponse with status_code not set, defaulting to 200. This is semantically wrong — an invalid token is a not-found condition. It also means the test at test_games.py:135 asserts 200, encoding the wrong behavior. | **Suggested Fix**: Pass status_code=404 to the TemplateResponse when the token is invalid, matching the POST handler's behavior.

