---
id: loo-t13y
status: closed
deps: []
links: []
created: 2026-02-25T04:50:19Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:perf]
---
# Double DB round-trip on first session0 visit due to post-seed re-query

**File**: loom/routers/session0.py
**Line(s)**: 114-133
**Description**: In session0_index, when no prompts exist for a game (first visit), _seed_defaults seeds the rows and commits, then immediately fires a second SELECT to reload them. This results in two round-trips to the database where one is sufficient. The pattern is: INSERT (via flush), commit, then SELECT — the in-session objects are discarded and re-fetched from scratch.
**Suggested Fix**: After _seed_defaults + db.flush(), read the prompts from the SQLAlchemy identity map rather than re-querying. Since _seed_defaults calls db.flush() the objects are already tracked in the session. Use db.commit() then derive the active prompt from the already-flushed objects, or return the newly created prompt objects directly from _seed_defaults so the caller does not need to re-query.
**Importance**: Medium

