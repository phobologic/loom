---
id: loo-90l5
status: closed
deps: []
links: [loo-ifdf]
created: 2026-02-25T02:30:01Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:readability]
---
# get_current_user raises HTTPException for redirect rather than using RedirectResponse

**File**: loom/dependencies.py lines 21 and 25. The dependency raises HTTPException(status_code=302, headers={'Location': '/dev/login'}) to perform a redirect. This is a known FastAPI workaround but it is non-obvious — HTTPException is semantically an error, not a redirect. The docstring mentions 'Redirects to /dev/login' which is helpful, but a future maintainer replacing this with OAuth may not realize that a 302 status on an HTTPException is the redirect mechanism. **Suggested Fix**: Add an inline comment explaining why HTTPException is used for the redirect (e.g., '# FastAPI dependencies cannot return RedirectResponse directly; HTTPException with 302 is the standard workaround'). The comment should survive the OAuth swap noted for Step 25.


## Notes

**2026-02-25T02:33:13Z**

Duplicate of loo-ifdf
