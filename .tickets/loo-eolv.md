---
id: loo-eolv
status: open
deps: [loo-1u6r]
links: []
created: 2026-02-26T19:51:54Z
type: bug
priority: 1
assignee: Michael Barrett
tags: [playwright]
---
# Tension adjustment vote resolves but scene tension value not updated

After scene completion, the tension adjustment section appeared correctly with AI recommendation (+1 Escalate). Both Alice and Bob voted +1. After all votes resolved, the section disappeared (correct). However, the scene tension value remained at 7/9 instead of updating to 8/9. The new scene form on the scenes list also defaulted to 7, not 8. The vote appears to record correctly but the DB update for the tension delta is missing or not applied to the scene record. Steps to reproduce: complete a scene, vote on tension adjustment (unanimous +1), then check the scene tension value on the scene detail page.


## Notes

**2026-02-26T20:23:47Z**

DESIGN CLARIFICATION: The fix should NOT update scene.tension on the completed scene — that value is historical record (the tension this scene ran at). Instead, the tension adjustment vote should write its resolved value to a new nullable field, e.g. tension_carry_forward on Scene. When proposing the next scene, default_tension reads scene.tension_carry_forward ?? scene.tension from the previous scene. Display on the completed scene detail can show 'Tension: 7 → 8 after scene' using both fields. Migration required to add tension_carry_forward column. The voting resolution code in scenes.py should write to tension_carry_forward instead of mutating tension.
