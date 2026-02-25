---
id: loo-8esb
status: closed
deps: []
links: []
created: 2026-02-25T04:51:45Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:readability]
---
# identity-map comment in session0_index route needs more context

**File**: loom/routers/session0.py
**Line(s)**: 776
**Description**: The comment '# Load prompts directly (avoids identity-map caching issues after seeding)' explains what is happening but not why the identity map would be stale here or what symptom would occur without this workaround. A developer unfamiliar with SQLAlchemy's session identity map may not understand the failure mode being avoided, making the code harder to maintain.
**Suggested Fix**: Expand the comment to explain that db.flush() inside _seed_defaults does not expire the Game.session0_prompts relationship on the already-loaded game object, so a fresh query is required to see the newly inserted rows. This makes the workaround self-documenting.

