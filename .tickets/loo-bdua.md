---
id: loo-bdua
status: open
deps: []
links: []
created: 2026-02-25T02:29:23Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:readability]
---
# test_auth.py duplicates the client fixture already present in test_games.py

**File**: tests/test_auth.py lines 10-17 and tests/test_games.py lines 15-24. Both files define an async client fixture that bootstraps the schema and seeds dev users via ASGITransport. The only difference is test_games.py adds a teardown (drop_all). conftest.py has an async_client fixture but it does not seed the DB, so tests needing seeded users cannot use it. **Suggested Fix**: Move the seeded-client fixture (with drop_all teardown) into conftest.py so both test files share it without duplication. The existing async_client fixture in conftest.py can be kept for tests that do not need seeded data.

