---
id: loo-ifdf
status: open
deps: []
links: [loo-90l5]
created: 2026-02-25T02:28:52Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# get_current_user uses HTTP 302 via HTTPException which loses body and may break non-browser clients

**File**: loom/dependencies.py
**Line(s)**: 21, 25
**Description**: Raising `HTTPException(status_code=302, headers={"Location": ...})` is an unusual pattern. FastAPI's HTTPException is not designed for redirects — it returns a JSON body with a 302 status, which works in a browser but silently fails for non-browser clients (e.g. HTMX fetch, future API clients) that do not follow redirects. FastAPI provides `RedirectResponse` specifically for this use case.
**Suggested Fix**: Replace both raises with `raise` using a custom exception class, or restructure the dependency to return `RedirectResponse` by catching the exception in the router. Better yet, use a `RedirectResponse` directly and raise it as `HTTPException` only as a last resort.

