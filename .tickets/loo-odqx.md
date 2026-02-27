---
id: loo-odqx
status: closed
deps: [loo-ofqu]
links: []
created: 2026-02-27T00:05:05Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-82fd
---
# Migrate test_games.py to shared fixtures

test_games.py uses _test_session_factory global for direct DB assertions after HTTP requests. Needs to be migrated to the shared client + db fixtures from conftest.py (loo-ofqu).

## Current pattern
```python
_test_session_factory: async_sessionmaker | None = None

@pytest.fixture
async def client():
    global _test_session_factory
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    _test_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    # ... create_all, seed, yield, drop_all, dispose
    _test_session_factory = None
```

Tests call: async with _test_session_factory() as db: ...

## New pattern
Replace with the shared client + db fixtures from conftest.py. Each test that uses _test_session_factory should add db as a fixture parameter:
  async def test_something(self, client, db):

Replace all: async with _test_session_factory() as db:
With: the db fixture parameter directly (no async with needed — already a session)

## Steps
1. Record baseline: time uv run pytest -v tests/test_games.py
2. Remove _test_session_factory global and local client fixture
3. Remove now-unused imports
4. Update all test methods that open _test_session_factory sessions to use the db fixture parameter instead
5. Run: time uv run pytest -v tests/test_games.py

Note: db is a single session shared across all operations within a test. The session is already open — no need for async with. Just call await db.execute(...), await db.scalar(...), etc.

28 tests in this file. Include before/after timings as a note on this ticket.


## Notes

**2026-02-27T03:47:53Z**

Before: 2.45s (28 tests). After: 0.85s. ~3x speedup. Removed _test_session_factory global and local client fixture; replaced all async with _test_session_factory() as db: blocks with direct db fixture parameter usage; added db.expire_all() before re-reads after HTTP writes.
