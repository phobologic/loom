---
id: loo-pggr
status: open
deps: [loo-1u6r]
links: []
created: 2026-02-26T20:09:47Z
type: bug
priority: 2
assignee: Michael Barrett
tags: [playwright]
---
# Challenge dismiss: comment thread not preserved after author dismisses

Workflow 20 (challenge dismiss): After Bob challenges a beat and adds a discussion comment, and Alice dismisses the challenge ('Dismiss — beat stands as written'), the beat correctly returns to [Canon] and the challenge reason disappears, but the comment Bob left during the challenge is also removed from view. Pass criteria requires 'comment thread remains visible in the beat display' after dismissal. Steps: 1) Submit a minor beat (Alice). 2) Bob challenges it. 3) Bob adds a comment. 4) Alice dismisses. 5) The comment is no longer visible on the scene page.


## Notes

**2026-02-26T20:14:08Z**

BROADER ISSUE: The original ticket captures only 'comments lost on dismiss'. The actual problem is wider — after ANY challenge resolution (both accept+revise and dismiss), the entire challenge record is erased: the original challenge reason, the discussion thread, and the outcome are all gone. The beat simply reverts to plain Canon with no indication a challenge ever occurred. Players should be able to see the challenge history (at minimum a collapsed/muted record showing 'Challenged by X: reason — Resolved [accepted revision / dismissed]'). Observed in smoke test screenshots 19-challenge-accept-pass.png and 20-challenge-dismiss-pass.png.
