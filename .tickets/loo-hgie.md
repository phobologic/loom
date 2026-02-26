---
id: loo-hgie
status: open
deps: [loo-vaim]
links: []
created: 2026-02-26T05:20:28Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-leil
---
# Step 37: AI-Suggested Character Updates

After scene completes, AI reviews recent beats and suggests additions to character sheets: new relationships, traits revealed through action, items acquired, goals changed. Presented privately to character's owning player. Player can accept, modify, or dismiss each suggestion. Accepted updates added to character document. Requirements: REQ-CHAR-003.


## Notes

**2026-02-26T05:28:28Z**

Additional requirement detail from REQ-CHAR-003:

**Trigger timing:** Suggestions fire after a scene completes *or periodically during play* — not only at scene boundaries. The 'periodically during play' path is less defined in the requirements but should be designed for: a background job or hook that reviews recent beats and surfaces suggestions without waiting for scene completion. The scene-completion trigger is the primary one; the periodic trigger is secondary and can be a follow-up if the scene-completion path proves sufficient.
