---
id: loo-hag2
status: closed
deps: []
links: [loo-wv26]
created: 2026-02-25T04:50:13Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# Referer-based redirect in safety tools / add is open to header spoofing

**File**: loom/routers/safety_tools.py
**Line(s)**: 113-115, 148-150
**Description**: Both add_safety_tool and delete_safety_tool use the Referer header for post-action redirect. The Referer header is user-controlled and can be set to an arbitrary URL by the client, allowing open redirect to any URL (including external sites). At minimum this leaks the redirect flow to attacker control; if the app later gains sensitive redirect handling, this becomes exploitable for phishing.
**Suggested Fix**: Remove the referer-based redirect and always redirect to a fixed, application-controlled URL such as /games/{game_id}/safety-tools. The referer convenience is not worth the open-redirect risk.


## Notes

**2026-02-25T04:54:58Z**

Duplicate of loo-wv26 (open redirect via Referer header in safety_tools.py)
