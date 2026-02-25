---
id: loo-wv26
status: in_progress
deps: []
links: [loo-hag2, loo-2lzh, loo-4w32]
created: 2026-02-25T04:50:02Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:security]
---
# Open Redirect via Referer header in safety_tools.py

**File**: loom/routers/safety_tools.py
**Line(s)**: 113-115, 147-149
**Description**: Both add_safety_tool and delete_safety_tool use the raw Referer header as a redirect target without any validation. An attacker can craft a form submission with a spoofed Referer header pointing to an arbitrary URL, causing the server to issue a 303 redirect to an attacker-controlled site (open redirect).
**Suggested Fix**: Validate that the referer URL shares the same origin (scheme + host + port) as the current request before using it as a redirect target. Alternatively, pass an explicit next= form parameter and validate that instead, or simply always redirect to the known safe URL (/games/{game_id}/safety-tools).

