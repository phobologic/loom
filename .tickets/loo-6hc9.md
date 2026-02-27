---
id: loo-6hc9
status: open
deps: [loo-1szi]
links: []
created: 2026-02-27T05:38:31Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-jy09
---
# Step 50: AI Nudge for Scene Completion

The AI monitors the fiction for signals that the current scene's guiding question has been resolved. When detected, a non-blocking suggestion is surfaced to all players. Players can dismiss it or initiate the completion proposal. The AI does not auto-complete scenes.

## Requirements

### REQ-SCENE-003: AI Nudge for Scene Completion
*Requirement:* When the AI detects that a scene's guiding question may have been answered, it shall suggest that the group consider completing the scene.
*Acceptance Criteria:*
- The AI monitors the fiction for signals that the current scene's guiding question has been resolved.
- When detected, a non-blocking suggestion is surfaced to all players.
- Players can dismiss the suggestion or initiate the completion proposal.
- The AI does not auto-complete scenes.

