---
id: loo-nqdj
status: closed
deps: []
links: [loo-yxpz]
created: 2026-02-25T04:50:08Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:perf]
---
# Redundant _find_membership helper duplicated across four routers

**File**: loom/routers/characters.py, loom/routers/safety_tools.py, loom/routers/session0.py, loom/routers/world_document.py
**Line(s)**: characters.py:22-26, safety_tools.py:22-26, session0.py:57-61, world_document.py:44-47
**Description**: The _find_membership(game, user_id) helper is copy-pasted verbatim into four different router modules. Each call performs a linear O(n) scan over game.members in Python. While the member count is bounded (max 5 players), the duplication means any future optimization or bug fix must be applied in four places. More importantly, every handler that needs both game data and a membership check executes this scan at least once per request — and several handlers (e.g. update_character, accept_synthesis) run the load plus the scan on every POST.
**Suggested Fix**: Extract to loom/routers/_common.py or loom/dependencies.py so it is defined once and imported everywhere. No algorithmic change is needed given the bounded size, but centralizing it eliminates the maintenance hazard.
**Importance**: Low


## Notes

**2026-02-25T04:55:13Z**

Duplicate of loo-yxpz (_find_membership duplicated across four routers)
