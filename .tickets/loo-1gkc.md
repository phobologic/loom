---
id: loo-1gkc
status: open
deps: [loo-t6ld]
links: []
created: 2026-02-25T01:22:44Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 21: Fortune Roll

Yes/no oracle. Player sets odds, tension modifies probability, roll executes, result displayed. Exceptional results flagged as major beats. Odds contestation window.

## Acceptance Criteria

### REQ-ORACLE-007: Fortune Roll (Yes/No Oracle)
*Requirement:* Loom shall provide a quick yes/no oracle for questions that don't need full narrative interpretations, using a weighted probability system.
*Acceptance Criteria:*
- Any player can ask a yes/no question and invoke a Fortune Roll.
- The asking player sets the odds: Impossible, Very Unlikely, Unlikely, 50/50, Likely, Very Likely, Near Certain.
- Loom rolls against the probability, modified by the current Tension, and returns one of four results: Exceptional Yes, Yes, No, or Exceptional No.
- The result and the odds setting are displayed to all players.
- Other players can contest the odds setting before the roll resolves. If no one contests within a short window (configurable, default: half the silence timer or 1 hour minimum), the roll resolves as set.
- Exceptional Yes and Exceptional No results are automatically flagged as major beats.
- Regular Yes and No results default to minor beats.
- A Fortune Roll can be embedded as an event within a beat.
- Word seeds are not used for Fortune Rolls.

---

### REQ-TENSION-001: Tension Tracking
*Requirement:* Loom shall track a Tension per scene that represents the current level of narrative tension and unpredictability.
*Acceptance Criteria:*
- The Tension is a value from 1 to 9, starting at 5 for the first scene of a game.
- The current Tension is visible to all players at all times (displayed alongside the scene information).
- The Tension carries forward from scene to scene within an act. When a new scene begins, it inherits the Tension from the previous scene.
- When a new act begins, the Tension resets to 5.

---

### REQ-TENSION-003: Tension Effects on Fortune Roll
*Requirement:* The Tension shall modify the probability of Fortune Roll results.
*Acceptance Criteria:*
- Higher tension increases the probability of "Yes" answers and exceptional results.
- Lower tension decreases the probability of "Yes" answers and exceptional results.
- At Tension 1, even "Likely" questions have a meaningful chance of "No".
- At Tension 5 (baseline), probabilities match the stated odds intuitively.
- At Tension 9, even "Unlikely" questions have a real chance of "Yes," and exceptional results are common.
- The probability table is documented and transparent to players (not a hidden mechanic).

