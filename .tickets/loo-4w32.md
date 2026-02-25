---
id: loo-4w32
status: closed
deps: []
links: [loo-wv26]
created: 2026-02-25T04:51:23Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:readability]
---
# Referer-based redirect in safety_tools add/delete routes is undocumented and untested

**File**: loom/routers/safety_tools.py
**Line(s)**: 590-593, 630-633
**Description**: Both add_safety_tool and delete_safety_tool redirect to the HTTP Referer header if present, falling back to the canonical /safety-tools URL. This behaviour is not mentioned in the docstrings, is not covered by any test, and relies on a user-supplied header which can be absent or spoofed. The comment in add_safety_tool says 'redirect back to where they came from' only implicitly via the code. Any future caller from a different page would silently inherit this redirect behaviour.
**Suggested Fix**: Document the Referer-redirect behaviour in each handler's docstring. Add at least one test case that verifies the fallback URL when no Referer is present. Consider whether this redirect policy should be an explicit 'next' query parameter instead of relying on the Referer header, which is a more robust and auditable pattern.


## Notes

**2026-02-25T04:54:58Z**

Duplicate of loo-wv26 (readability/docs aspect covered, but core issue is the same open redirect)
