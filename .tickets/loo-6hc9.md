---
id: loo-6hc9
status: closed
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


## Notes

**2026-02-28T16:16:38Z**

Implemented AI nudge for scene completion (REQ-SCENE-003).

New DB table: scene_completion_suggestions (migration b3c4d5e6f7a8).
Fields: scene_id, last_checked_beat_id (FK beats), ai_rationale, confidence_score (1-10), status (pending/dismissed/evaluated).

AI function suggest_scene_completion() in loom/ai/client.py returns (confidence: int, rationale: str).
Schema: SceneCompletionNudgeResponse with confidence (1-10) and rationale fields.

Background task _check_and_suggest_scene_completion() fires from scene_detail page load when:
- scene is active
- no pending suggestion exists
- no open scene_complete proposal
- >= 5 IC canon beats
- >= 5 new IC canon beats since last check (tracked via last_checked_beat_id FK)

Confidence threshold: >= 6 creates a pending suggestion; below that, creates evaluated row (tracking only).
On high confidence: notifies all game members with NotificationType.scene_completion_suggested.

UI: green dismissable card in scene_detail.html showing rationale and confidence score.
Buttons: Propose Scene Completion (posts to existing /complete route) and Dismiss.
Auto-dismiss: pending suggestion dismissed when scene_complete proposal is created.

Dismiss route: POST /games/{game_id}/acts/{act_id}/scenes/{scene_id}/completion-suggestion/{id}/dismiss.

Tests: 7 new tests in TestSceneCompletionNudge in test_scenes.py.
Smoke manifest: entry 36 added.
conftest.py: _suggest_scene_completion mock added (returns (0, '') so no nudges fire in tests).
