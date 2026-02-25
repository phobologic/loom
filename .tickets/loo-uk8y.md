---
id: loo-uk8y
status: open
deps: []
links: [loo-onjn]
created: 2026-02-25T02:29:22Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# test fixtures share a single persistent database file across test modules — no isolation

**File**: tests/test_auth.py line 13, tests/test_games.py line 17 | **Description**: Both test modules call engine.begin() + create_all on the shared loom.database.engine which points to the file-based loom.db. test_games.py drops tables on teardown but test_auth.py does not. Tests that run in parallel or in a different order can interfere with each other. The db_session fixture in test_models.py correctly uses an in-memory database. | **Suggested Fix**: Override the database URL in tests to use sqlite+aiosqlite:///:memory: and rebuild the engine per test session, or use a tmp_path-based file. Each integration test fixture should create and drop its own schema.

