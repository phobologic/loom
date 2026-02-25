---
id: loo-4nd5
status: closed
deps: [loo-oizg]
links: []
created: 2026-02-25T01:22:42Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 12: Scene Creation + Character Presence

Propose a scene with guiding question, initial characters present, optional location. Goes through voting. Characters present list is displayed and updatable.

## Acceptance Criteria

### REQ-SCENE-001: Scene Creation
*Requirement:* When an act is active, Loom shall allow players to propose a new scene.
*Acceptance Criteria:*
- Any player can propose a new scene within the active act.
- The proposal includes: a title (optional), a description (optional), a guiding question (required), which characters are present (required), and a location (optional, can reference an existing world entry or create a new one).
- Scene creation is treated as a major beat and requires group approval.
- The AI can suggest possible next scenes based on where the fiction left off, including proposed guiding questions.
- Multiple scenes cannot be active simultaneously in v1.

---

### REQ-SCENE-004: Scene Character Presence
*Requirement:* Loom shall track which characters are currently present in an active scene as a dynamic, point-in-time list.
*Acceptance Criteria:*
- When a scene is created, the proposer specifies which characters are initially present.
- The "Characters Present" list is a living indicator of who is in the scene *right now*, not a historical record.
- When a character enters the scene (via a narrative beat), Loom updates the list to include them.
- When a character leaves the scene (via a narrative beat), Loom updates the list to remove them.
- Any player can update the presence list for their own character. Updating presence for NPCs or other players' characters follows the normal beat proposal flow.
- The Characters Present list is visible to all players at all times alongside the scene information.
- The Characters Present list is included in the AI context for oracle queries, prose expansion, and other AI features.
- The full history of who was present and when is derivable from the beat timeline and does not need separate tracking.

