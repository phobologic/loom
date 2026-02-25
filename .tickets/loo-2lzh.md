---
id: loo-2lzh
status: closed
deps: []
links: [loo-wv26]
created: 2026-02-25T04:51:02Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:perf]
---
# Referer-based redirect in safety_tools trusts an unvalidated client header

**File**: loom/routers/safety_tools.py
**Line(s)**: 117-119, 147-149
**Description**: Both add_safety_tool and delete_safety_tool redirect to request.headers.get('referer') without any validation. While this is not a pure performance issue, it is a resource-routing concern: a malicious or misconfigured client can supply an arbitrary Referer header and cause the server to issue a 303 redirect to any URL, including external ones. This constitutes an open redirect vulnerability.
**Suggested Fix**: Validate that the referer URL belongs to the same host before using it, or remove the referer fallback entirely and always redirect to /games/{game_id}/safety-tools (the destination is predictable and already known).
**Importance**: High


## Notes

**2026-02-25T04:51:24Z**

Note from reviewer: The open-redirect risk is present in both POST handlers (add_safety_tool at line 117-119 and delete_safety_tool at lines 147-149). The simplest safe fix is:

from urllib.parse import urlparse

def _safe_redirect(referer: str | None, fallback: str, request: Request) -> str:
    if referer:
        parsed = urlparse(referer)
        if not parsed.netloc or parsed.netloc == request.headers.get('host'):
            return referer
    return fallback

This is both a security and a resource-routing concern (prevents redirect to offsite resources).

**2026-02-25T04:54:58Z**

Duplicate of loo-wv26 (same open redirect vulnerability, different reviewer)
