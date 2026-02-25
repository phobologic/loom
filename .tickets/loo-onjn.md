---
id: loo-onjn
status: closed
deps: []
links: [loo-uk8y]
created: 2026-02-25T02:29:36Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:perf]
---
# Test fixtures in test_auth.py and test_games.py do not isolate database state

**File**: tests/test_auth.py (lines 10-17), tests/test_games.py (lines 15-24)
**Line(s)**: test_auth.py:10-17, test_games.py:15-24
**Description**: Both test files share the same SQLite file-backed database (sqlite+aiosqlite:///./loom.db from config.py). The test_games.py fixture drops tables after each test, but test_auth.py does not — it only creates tables and seeds users. If tests from both files run in the same session, residual state from test_auth.py can leak into test_games.py (or vice versa if ordering changes), causing flaky failures.

Additionally, because these fixtures recreate the full schema and seed data on every test, the startup cost is multiplied by the number of tests. The test_models.py fixture correctly uses an in-memory SQLite database per test, which is both faster and fully isolated.

**Suggested Fix**: Use sqlite+aiosqlite:///:memory: in the test client fixtures the same way test_models.py does, or ensure a drop_all teardown is always present. Consider a session-scoped or module-scoped fixture to avoid recreating the schema for every single test function.


## Notes

**2026-02-25T02:32:58Z**

Duplicate of loo-uk8y
