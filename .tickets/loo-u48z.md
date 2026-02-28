---
id: loo-u48z
status: closed
deps: [loo-3k60]
links: []
created: 2026-02-27T05:36:55Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-jy09
---
# Step 48: Act Narrative Compilation

When an act is completed (and auto-narrative is enabled), the AI generates a prose narrative for the act, incorporating scene narratives and the act's overall arc. Uses the act's guiding question and resolution as framing. Stored with the act and viewable by all players. Read-only in v1.

## Requirements

### REQ-PROSE-003: Act Narrative Compilation
*Requirement:* When an act is completed, Loom shall generate a compiled narrative for the act.
*Acceptance Criteria:*
- If auto-narrative is enabled, the AI generates a prose narrative for the completed act, incorporating scene narratives and the act's overall arc.
- The act narrative uses the act's guiding question and resolution as framing.
- The narrative is stored with the act and viewable by all players.
- The narrative is read-only in v1.


## Notes

**2026-02-28T15:33:26Z**

Implemented act narrative compilation. Added Act.narrative column (migration f0a1b2c3d4e5), ActNarrativeResponse schema, assemble_act_narrative_context() in context.py, generate_act_narrative() in client.py, and _compile_act_narrative() in acts.py. Hooked into both auto-approve path (propose_act_complete) and vote-approval path (cast_vote in world_document.py via import). Template scenes.html shows narrative in purple-bordered box when act is complete. conftest.py mocks the new AI function. 4 new tests in TestActNarrative cover auto-approve, vote-approval, disabled setting, and template display. Smoke manifest entry 18b added. No circular import issues - world_document.py already had a safe import path to acts.py.
