---
id: loo-m6rd
status: open
deps: []
links: []
created: 2026-02-28T15:50:31Z
type: task
priority: 4
assignee: Michael Barrett
parent: loo-1pwe
---
# Audit AI calls for efficiency and redundancy

Review all AI calls in loom/ai/client.py and call sites across routers to identify inefficiencies: redundant calls, opportunities to batch or cache results, unnecessary context being sent, and calls that could be eliminated entirely. Look for patterns like the same AI function being called multiple times per user action, or large context windows being built for simple tasks.

