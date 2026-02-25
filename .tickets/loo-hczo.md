---
id: loo-hczo
status: closed
deps: []
links: []
created: 2026-02-25T02:29:28Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:readability]
---
# test_auth.py client fixture missing drop_all teardown unlike test_games.py

**File**: tests/test_auth.py lines 10-17. The client fixture creates schema and seeds users but never drops the schema on teardown. tests/test_games.py (lines 22-23) correctly adds drop_all after yield. Without teardown, the shared SQLite database file (loom.db) accumulates state across test runs, which can cause non-deterministic failures when tests in test_auth.py are run after others. **Suggested Fix**: Add teardown to the fixture: after 'yield c', add 'async with engine.begin() as conn: await conn.run_sync(Base.metadata.drop_all)'. Better still, consolidate both fixtures into conftest.py (see related ticket).

