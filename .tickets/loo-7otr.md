---
id: loo-7otr
status: open
deps: [loo-5w9l]
links: []
created: 2026-02-27T05:39:25Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-jy09
---
# Step 53: Tension Voting Mode Setting

Allow games to choose between two modes for tension adjustment on scene completion. Configurable by the organizer in game settings.

Note: loo-8f28 is an open standalone ticket with identical scope created during Phase 2 work. Close loo-8f28 when this ticket is started.

## Requirements

### REQ-TENSION-002 (extension): Tension Voting Mode Setting
*Requirement:* Allow games to choose between two modes for tension adjustment on scene completion.
*Acceptance Criteria:*
- 'vote' (default): current behavior - AI proposes a delta, players each vote (+1/0/-1), plurality wins.
- 'ai_auto': AI suggestion is applied immediately to tension_carry_forward on scene completion; no vote UI shown. Intended for groups who want frictionless flow and trust the oracle to manage tension.
- Configurable by the organizer in game settings.
- When ai_auto is active, the tension adjustment section is suppressed from the scene detail page.
- The smoke manifest notes that workflow 18 only applies when tension_voting_mode='vote'.
- Implementation touchpoints: models.py (add tension_voting_mode column to Game), Alembic migration, scenes.py (branch on mode at scene completion), scene_detail.html (suppress vote UI), game_settings.html (add organizer form field), smoke-manifest.md (annotate workflow 18).

