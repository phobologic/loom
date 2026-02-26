---
id: loo-6dp5
status: closed
deps: [loo-c1sd]
links: []
created: 2026-02-26T05:19:50Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-leil
---
# Step 31: Challenge System - Resolution

Beat author sees the challenge reason and can either accept it (submit revised content → beat re-enters approval vote as a major beat) or dismiss it (beat returns to canon, challenger and all members notified). Any game member can post comments on the challenged beat to discuss the concern — the author reads the discussion and decides. No group vote; no forced changes; author has final say on their own canon content.

Adds: BeatComment model + migration, accept/dismiss endpoints, comment thread on challenged beats. Also removes TieBreakingMethod.challenger (dead code after removing challenge vote system) and updates requirements + design principles to capture the collaborative philosophy.

Requirements: REQ-CHALLENGE-002, REQ-CHALLENGE-003.

