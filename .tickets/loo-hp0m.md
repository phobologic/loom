---
id: loo-hp0m
status: closed
deps: [loo-4nd5]
links: []
created: 2026-02-25T01:22:42Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 13: Scene View + Beat Timeline

The main play view. Scene info (guiding question, characters present, tension), beat timeline in chronological order, beat submission area (placeholder). Start with displaying beats only.

Wire up **HTMX polling** on the timeline here (hx-trigger='every 5s') so new beats from other players appear without a page reload.

## Acceptance Criteria

### REQ-BEAT-006: Beat Timeline Display
*Requirement:* Loom shall display beats in a chronological timeline within each scene.
*Acceptance Criteria:*
- The timeline shows all beats in order of submission.
- Each beat displays: the author, the timestamp, the significance level, the current status, and all contained events.
- The timeline supports filtering by event type (show only IC content, show only OOC, show all).
- Beats with pending votes or active challenges are visually distinguished.

---

### REQ-TENSION-001: Tension Tracking
*Requirement:* Loom shall track a Tension per scene that represents the current level of narrative tension and unpredictability.
*Acceptance Criteria:*
- The Tension is a value from 1 to 9, starting at 5 for the first scene of a game.
- The current Tension is visible to all players at all times (displayed alongside the scene information).
- The Tension carries forward from scene to scene within an act. When a new scene begins, it inherits the Tension from the previous scene.
- When a new act begins, the Tension resets to 5.

