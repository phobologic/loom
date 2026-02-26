---
id: loo-u2nv
status: closed
deps: [loo-nhgl]
links: []
created: 2026-02-25T01:22:44Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 23: AI Integration - Real Calls

Replace all stubbed AI with real Anthropic API calls through the abstraction layer. Context assembly, per-feature model configuration. Covers oracle, Session 0 synthesis, world document generation, significance classification.

## Acceptance Criteria

### REQ-AI-001: AI Provider Abstraction
*Requirement:* Loom shall abstract AI interactions behind a generic interface so that the underlying provider can be changed without affecting the rest of Loom.
*Acceptance Criteria:*
- All AI calls go through a common interface/abstraction layer.
- The initial implementation uses Anthropic's API (Claude).
- Switching to a different provider requires changes only in the provider implementation, not in calling code.
- The interface supports: text generation (for oracle, prose expansion, narrative compilation, Session 0 synthesis), classification (for beat significance, consistency checking), and suggestion generation.

---

### REQ-AI-003: AI Context Assembly
*Requirement:* When assembling context for any AI call, Loom shall include relevant game state without sending the entire game history.
*Acceptance Criteria:*
- Standard context includes: world document, current act guiding question, current scene guiding question and description, characters currently present in the scene, relevant NPC entries, recent beat history (configurable window), and lines and veils.
- Loom avoids sending all beats or all scenes.
- Context is assembled fresh for each call to reflect the current game state.
- Lines and veils are always included and the AI is instructed to respect them.

---

### REQ-AI-004: Model Configuration Per Feature
*Requirement:* Loom shall allow configuration of which AI model is used for each type of AI interaction, enabling cost and quality optimization.
*Acceptance Criteria:*
- Each AI feature is mapped to a configurable model selection. Features include: beat significance classification, pre-submission consistency checking, oracle interpretive generation, Fortune Roll exceptional result follow-up, prose expansion, scene/act narrative compilation, Session 0 synthesis, character/NPC/world update suggestions, scene/act completion nudge detection, and Tension adjustment evaluation.
- Default model assignments: lightweight tasks (classification, nudge detection) default to a smaller/cheaper model (e.g., Haiku). Creative tasks (oracle, prose expansion, narrative compilation, Session 0 synthesis) default to a more capable model (e.g., Sonnet).
- Model assignments are configurable by system administrators only.
- Model assignment changes take effect on new AI calls without requiring a restart.
- AI usage tracking records which model was used for each call.

