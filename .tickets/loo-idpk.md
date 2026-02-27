---
id: loo-idpk
status: open
deps: [loo-9gyk]
links: []
created: 2026-02-27T05:38:52Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-jy09
---
# Step 52a: Random Events - Scene Start

At the start of each new scene, Loom rolls to determine if the scene is altered or interrupted based on the current tension. Higher tension means higher probability of disruption. An "altered" scene gets a suggested modification (something is different from what the players expected). An "interrupted" scene gets an entirely different scene suggestion using a word seed pair for inspiration. The group can accept (replacing their proposed scene), weave it in (modifying their scene to include the interruption), or reject it (proceeding as planned, but the rejected event is noted as a potential future thread).

This is the first half of REQ-TENSION-005. The second half (Fortune Roll doubles trigger) is Step 52b, which builds on the word-seed + AI generation infrastructure established here.

## Requirements

### REQ-TENSION-005 (scene-start trigger): Random Events at Scene Start
*Requirement:* At the start of each new scene, Loom shall roll to determine if the scene is altered or interrupted based on the current Tension.
*Acceptance Criteria:*
- At the start of each new scene, Loom rolls to determine if the scene is altered or interrupted. Higher tension = higher probability of disruption.
- An "altered" scene: AI suggests a modification to the proposed scene setup (something is different from what players expected). Shown to the group, who can accept, modify, or reject.
- An "interrupted" scene: AI suggests an entirely different scene driven by a random event, using a word seed pair for inspiration. The group can: accept (replacing their proposed scene), weave it in (modifying their proposed scene to include the interruption), or reject (proceeding as planned, with the rejected event noted as a potential future thread).
- At low tension (1-3), random events are very rare. At high tension (7-9), they are frequent and disruptive.

