---
id: loo-82fd
status: open
deps: []
links: []
created: 2026-02-27T00:03:47Z
type: epic
priority: 2
assignee: Michael Barrett
---
# Test suite performance: migrate to module-scoped DB + savepoint pattern

The test suite has 360 integration tests, each creating a fresh SQLite in-memory database (create_all + seed + drop_all) per test. This costs ~71ms per test in setup/teardown overhead alone — roughly 25 seconds of pure overhead across the suite.

The fix is the standard SQLAlchemy testing pattern:
- Create the schema once per module (scope="module") using StaticPool
- Per test: open a connection, begin an outer transaction, yield, then rollback — schema stays intact, test data disappears

PILOT COMPLETE: test_auth.py has already been migrated (7 tests, db_engine fixture now in conftest.py). Full suite still passes.

Context from the pilot in tests/conftest.py and tests/test_auth.py.

