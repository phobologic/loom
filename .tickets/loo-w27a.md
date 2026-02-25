---
id: loo-w27a
status: closed
deps: []
links: []
created: 2026-02-25T02:29:07Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:security]
---
# CSRF protection absent on all state-changing POST forms

**File**: loom/templates/games.html, game_detail.html, game_settings.html, invite.html, dev_login.html | **Line(s)**: All HTML form elements | **Description**: No CSRF tokens are included in any POST form and no CSRF middleware is configured. Starlette SessionMiddleware does not provide CSRF protection. An attacker can craft a malicious page that silently submits requests to create games, change settings, regenerate/revoke invite links, or log a user out, provided the victim is authenticated. | **Suggested Fix**: Add itsdangerous- or starlette-based CSRF middleware (e.g. starlette-csrf or a custom double-submit cookie pattern) and inject a hidden csrf_token field into every POST form.


## Notes

**2026-02-25T02:39:17Z**

Closing: intentionally deferred. CSRF protection is relevant when real users have real sessions that can be forged. With dev auth only (no real users, no production deployment), there are no sessions worth protecting. Revisit when Step 25 (Real Auth) ships.
