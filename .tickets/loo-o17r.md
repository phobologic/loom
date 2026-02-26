---
id: loo-o17r
status: closed
deps: [loo-1u6r]
links: []
created: 2026-02-26T20:14:15Z
type: bug
priority: 1
assignee: Michael Barrett
tags: [playwright]
---
# Completed acts not linked from acts list — scenes inaccessible via UI

On /games/{id}/acts, completed acts are rendered as plain unlinked text (e.g. 'The Iron Contract (Complete)'). There is no link to navigate to the act's scenes list (/games/{id}/acts/{act_id}/scenes). The page is still accessible by direct URL (HTTP 200 confirmed), but there is no UI path to reach it. Players cannot review what transpired in a completed act without knowing the URL. Fix: completed acts in the acts list should link to their scenes list, the same as active acts do. Observed in smoke test screenshot 17-act-completion-pass.png.

