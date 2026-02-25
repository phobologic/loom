---
id: loo-yxpz
status: closed
deps: []
links: [loo-nqdj, loo-gm7b]
created: 2026-02-25T04:50:16Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:readability]
---
# Duplicated _find_membership helper across four routers

**File**: loom/routers/characters.py, loom/routers/safety_tools.py, loom/routers/session0.py, loom/routers/world_document.py
**Line(s)**: characters.py:19-22, safety_tools.py:498-503, session0.py:693-698, world_document.py:1259-1263
**Description**: The _find_membership(game, user_id) helper is copy-pasted identically into all four new routers. Any future change (e.g. supporting suspended members, logging access) must be made in four places. The function belongs in a shared location — either loom/routers/_helpers.py or loom/dependencies.py alongside get_current_user.
**Suggested Fix**: Extract to a shared module (e.g. loom/routers/_helpers.py) and import it in each router. The same pattern applies to the load-game helpers if they continue to diverge.

