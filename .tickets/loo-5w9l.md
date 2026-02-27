---
id: loo-5w9l
status: open
deps: [loo-idpk]
links: []
created: 2026-02-27T05:39:01Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-jy09
---
# Step 52b: Random Events - Fortune Roll Doubles

During play, when a Fortune Roll rolls doubles and the individual digit is equal to or less than the current tension, a random event fires alongside the Fortune Roll result. The AI generates a brief complication or twist using a word seed pair and the current context. Builds on the word-seed + AI generation infrastructure from Step 52a.

## Requirements

### REQ-TENSION-005 (Fortune Roll doubles trigger): Random Events During Play
*Requirement:* During play, when a Fortune Roll rolls doubles and the individual digit is <= the current Tension, a random event fires alongside the Fortune Roll result.
*Acceptance Criteria:*
- When a Fortune Roll result is doubles (e.g., 3-3, 5-5) AND the individual digit is <= current Tension, a random event is triggered.
- The AI generates a brief complication or twist using a word seed pair and the current context.
- The random event is presented alongside the Fortune Roll result.
- Random events are suggestions to the group, not forced into the fiction - they follow the standard beat proposal and approval flow.
- At low tension (1-3), this fires very rarely. At high tension (7-9), it fires frequently.

