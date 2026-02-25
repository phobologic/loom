---
id: loo-1e4u
status: closed
deps: []
links: []
created: 2026-02-25T04:51:06Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:security]
---
# Dev-only authentication mechanism lacks environment guard

**File**: loom/main.py (lines 19-37), loom/dependencies.py (lines 15-32)
**Description**: The application bootstraps three hardcoded dev users (Alice, Bob, Charlie) and the get_current_user dependency comment notes 'Swap this dependency for real OAuth in Step 25'. The _AuthRedirect exception handler redirects unauthenticated requests to /dev/login. There is no environment-level guard (e.g., checking settings.debug or an environment variable) to prevent the dev login route from being reachable in a production deployment. If this application were deployed before Step 25, any visitor could authenticate as any of the three pre-seeded users.
**Suggested Fix**: Add an explicit guard in the dev login routes and the user-seeding lifespan that raises an error or is a no-op when not in a development environment:
```python
if not settings.debug:
    raise HTTPException(status_code=404, detail='Not found')
```
Alternatively, ensure CI/deployment gates prevent production deployment until real auth is implemented.

