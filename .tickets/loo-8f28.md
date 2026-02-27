---
id: loo-8f28
status: closed
deps: [loo-1u6r]
links: []
created: 2026-02-26T20:27:55Z
type: feature
priority: 3
assignee: Michael Barrett
---
# Add tension_voting_mode game setting (vote vs ai_auto)

Add a tension_voting_mode setting to Game with two values:
- 'vote' (default): current behavior — after scene completion, create a tension adjustment vote proposal and let players vote. Auto-resolves on expiry or when next scene is proposed (see auto-resolve ticket).
- 'ai_auto': AI suggestion is applied immediately to tension_carry_forward on scene completion, no vote proposal is created and no voting UI is shown.

Useful for groups who want frictionless flow and trust the oracle to manage tension escalation.

Implementation touchpoints:
- models.py: add tension_voting_mode column to Game (string or enum, default 'vote')
- Alembic migration
- scenes.py: on scene completion, branch on tension_voting_mode — either create the vote proposal (vote) or immediately write tension_carry_forward (ai_auto)
- scene_detail.html: suppress tension adjustment UI when mode is ai_auto
- game_settings.html: add the setting to the organizer settings form
- smoke-manifest.md: note that workflow 18 applies only when tension_voting_mode='vote'


## Notes

**2026-02-27T05:39:31Z**

Superseded by Phase 3 Step 53 ticket (loo-7otr), parented to the Phase 3 epic (loo-jy09). Close this ticket when Step 53 is started.
