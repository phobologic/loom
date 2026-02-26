---
id: loo-ow8p
status: closed
deps: [loo-1u6r]
links: []
created: 2026-02-26T20:09:48Z
type: bug
priority: 1
assignee: Michael Barrett
tags: [playwright]
---
# Spotlight beat submission crashes with 500: notification_type vs ntype parameter mismatch

Workflow 23 (spotlight): When Alice submits a beat with a spotlight character selected (spotlighting Brother Cain, owned by Bob), the server returns HTTP 500 Internal Server Error. The page renders 'Internal Server Error' and the beat is not saved. Root cause: loom/routers/scenes.py line ~945 calls create_notification() with keyword argument notification_type=NotificationType.spotlight, but the function's parameter is named ntype=. This TypeError crashes the request handler whenever a spotlight notification is sent to a different player. Fix: change notification_type= to ntype= at the call site.

