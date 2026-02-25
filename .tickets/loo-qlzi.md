---
id: loo-qlzi
status: open
deps: [loo-2c8x]
links: []
created: 2026-02-25T01:22:41Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 7: Safety Tools

Lines and veils interface within Session 0. Any player can add them. Stored with the game and visible to all members. Can also be added later during play.

## Acceptance Criteria

### REQ-S0-006: Safety Tools
*Requirement:* During Session 0, Loom shall provide a way for players to establish content boundaries.
*Acceptance Criteria:*
- Players can define "lines" (hard limits - content that must not appear).
- Players can define "veils" (content that can be referenced but not depicted in detail - fade to black).
- Lines and veils are stored as part of the game configuration.
- Lines and veils are included in AI context so that oracle suggestions and prose expansion respect them.
- Any player can add new lines or veils at any time during play (not just Session 0).

