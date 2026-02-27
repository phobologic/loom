---
id: loo-te24
status: closed
deps: [loo-ofqu]
links: []
created: 2026-02-27T00:04:49Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-82fd
---
# Migrate test_models.py to shared db fixture

test_models.py uses a db_session fixture (not client) for pure ORM tests with no HTTP layer. It has the same create_all/drop_all overhead problem.

## Current pattern (in test_models.py)
```python
@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

## New pattern
Replace the local db_session fixture with a request of the shared db fixture from conftest.py (loo-ofqu). Rename all db_session references in the test file to db.

If test_models.py tests need users seeded (check whether any test depends on _DEV_USERS), the shared db fixture via db_conn already seeds them. If the models tests don't need dev users, the shared db fixture still works fine — the seeded rows are rolled back either way.

## Verification — measure the speedup
Record baseline BEFORE:
  time uv run pytest -v tests/test_models.py

Record result AFTER:
  time uv run pytest -v tests/test_models.py

21 tests. Expected: 21 create_all/drop_all cycles replaced with 1 (module-scoped). Include both timings as a note on this ticket.


## Notes

**2026-02-27T00:42:22Z**

Baseline: 1.67s (21 tests, 5.9s wall). After: 0.53s (4.1s wall). 3.2x speedup on test execution time.
