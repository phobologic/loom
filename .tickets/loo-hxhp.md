---
id: loo-hxhp
status: closed
deps: []
links: []
created: 2026-02-26T05:19:23Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-leil
---
# Step 26: Scene Completion + Act Completion

Any player proposes completing the current scene or act, group votes, on approval it's marked complete and becomes read-only. No AI nudges (Phase 3), no narrative generation (Phase 3) - just the state transition. Requirements: REQ-SCENE-002, REQ-ACT-002 (without AI nudge portions).


## Notes

**2026-02-26T05:28:38Z**

Clarification on scope and deferred portions:

**What is being implemented here:** The state machine transitions only — any player proposes, group votes via the standard voting mechanism, approved scene/act is marked complete and becomes read-only.

**What is NOT implemented here (Phase 3):**
- AI narrative compilation on scene completion (REQ-PROSE-002) — Phase 3
- AI narrative compilation on act completion (REQ-PROSE-003) — Phase 3
- AI nudge suggesting scene completion (REQ-SCENE-003) — Phase 3
- AI nudge suggesting act completion (REQ-ACT-003) — Phase 3

**Why this is Phase 2 despite REQ-SCENE-002/REQ-ACT-002 being Phase 3 requirements:** REQ-TENSION-002 (tension adjustment on scene completion, also Phase 2) requires a scene completion event to hook into. This ticket provides that hook. Implement scene/act completion as a state transition with an event/hook that downstream features (tension adjustment, and later narrative generation) can attach to.

**Phrasing fix:** The original ticket said 'without AI nudge portions' — this was imprecise. AI nudges (REQ-SCENE-003/REQ-ACT-003) are a separate requirement. What is actually deferred is the *narrative compilation* (REQ-PROSE-002/REQ-PROSE-003).
