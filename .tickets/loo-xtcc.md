---
id: loo-xtcc
status: closed
deps: [loo-ofqu]
links: []
created: 2026-02-27T00:04:57Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-82fd
---
# Migrate test_fortune_roll.py to shared fixtures

test_fortune_roll.py uses _test_session_factory global for direct DB assertions after HTTP requests. Needs to be migrated to the shared client + db fixtures from conftest.py (loo-ofqu).

## Current pattern
The file has a global _test_session_factory variable set by the client fixture. Tests call:
  async with _test_session_factory() as db:
      result = await db.execute(...)

## New pattern
Replace the global pattern with the shared db fixture from conftest.py. Any test that currently uses _test_session_factory should instead declare db as a fixture parameter:
  async def test_something(self, client, db):
      ...
      result = await db.execute(...)

The shared db fixture shares the same underlying connection/transaction as client, so HTTP-written data is visible to db queries.

## Steps
1. Record baseline: time uv run pytest -v tests/test_fortune_roll.py
2. Remove the _test_session_factory global and the local client fixture
3. Remove now-unused imports (create_async_engine, async_sessionmaker, Base, etc.)
4. Update test methods that use _test_session_factory: replace async with _test_session_factory() as db: with direct use of the db fixture parameter
5. Run: time uv run pytest -v tests/test_fortune_roll.py

Include both timings (before/after) as a note on this ticket. 22 tests in this file.


## Notes

**2026-02-27T01:18:20Z**

Baseline: 2.25s (22 tests, 6.0s wall). After: 1.12s (4.6s wall). 2x speedup on test execution time. Required two fixes in conftest.py: both override_get_db and db fixture sessions needed expire_on_commit=False to match production get_db — without this, server_default (func.now()) postfetch during commit triggered a MissingGreenlet error by crossing the async/greenlet boundary from outside greenlet_spawn context.
