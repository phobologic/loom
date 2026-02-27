---
id: loo-3k60
status: open
deps: [loo-mr8d]
links: []
created: 2026-02-27T05:35:59Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-jy09
---
# Step 47: Scene Narrative Compilation

When a scene is completed (and auto-narrative is enabled in game settings), the AI generates a prose narrative for the scene. Based on all narrative and roll events within the scene's beats, using the game's narrative voice and character voice notes. OOC events excluded. Stored with the scene and viewable by all players. Read-only in v1.

## Requirements

### REQ-PROSE-002: Scene Narrative Compilation
*Requirement:* When a scene is completed, Loom shall generate a compiled narrative for the scene.
*Acceptance Criteria:*
- If auto-narrative is enabled in game settings, the AI generates a prose narrative for the completed scene.
- The narrative is based on all narrative and roll events within the scene's beats, using the game's narrative voice and character voice notes.
- OOC events are excluded from the narrative.
- The narrative is stored with the scene and viewable by all players.
- The narrative is read-only in v1 (no collaborative editing).

