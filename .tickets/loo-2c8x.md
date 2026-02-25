---
id: loo-2c8x
status: open
deps: [loo-ad8u]
links: []
created: 2026-02-25T01:22:41Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 6: Session 0 - The Wizard Flow

The structured prompt sequence: genre, tone, setting, central tension, themes. Players contribute text to each prompt, see each other's contributions. AI synthesis is stubbed (returns realistic placeholder prose per the AI Stub Contract). Players can navigate forward/back through prompts.

## Acceptance Criteria

### REQ-S0-001: Session 0 Flow
*Requirement:* When a game is in the "setup" state, Loom shall guide players through a collaborative Session 0 process to establish the shared fiction.
*Acceptance Criteria:*
- The flow consists of a structured sequence of prompts covering: genre, tone, setting, central tension/mystery, themes, and safety tools (lines and veils).
- The game creator's initial pitch/description is presented as a starting point.
- Players can skip, reorder, or add custom prompts.
- Each prompt allows all players to contribute ideas.

---

### REQ-S0-002: AI Synthesis During Session 0
*Requirement:* When players provide input during Session 0 prompts, Loom shall use AI to synthesize contributions into coherent proposals.
*Acceptance Criteria:*
- The AI reads all player contributions for a given prompt and generates a synthesized version (e.g., "Three of you mentioned noir elements, one mentioned fantasy - here are some ways those could combine").
- Players can accept, modify, or request regeneration of the AI synthesis.
- The AI provides suggestions and guidance throughout the process to help groups that are unsure.

NOTE: AI is stubbed in this step. The stub must return realistic placeholder prose (not empty), per the AI Stub Contract.

