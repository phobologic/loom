---
id: loo-bav4
status: closed
deps: []
links: []
created: 2026-02-27T00:04:08Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-82fd
---
# Document test fixture conventions in CLAUDE.md

Add a testing conventions section to CLAUDE.local.md that prevents the per-test create_all/drop_all anti-pattern from being reintroduced in future tests.

## What to document

The rule: never create a per-test SQLite engine with create_all/drop_all. This costs ~71ms per test and compounds across hundreds of tests.

The correct pattern uses two fixtures from conftest.py:
- `client` — HTTP test client; the DB is seeded with dev users, all writes are rolled back after the test
- `db` — direct SQLAlchemy session on the same transaction (use when you need to assert DB state after an HTTP request)

Example of what NOT to do (the old pattern):
```python
@pytest.fixture
async def client():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    # ... create_all, seed, yield, drop_all, dispose  # WRONG
```

Example of what TO do:
```python
async def test_something(client, db):  # just request the fixtures
    response = await client.post('/games', data={'name': 'My Game'})
    game = await db.scalar(select(Game).where(Game.name == 'My Game'))
    assert game is not None
```

Also add a short module docstring to conftest.py explaining the two-fixture design and rollback guarantee.

## Verification
- Read CLAUDE.local.md and confirm the section is present
- Read tests/conftest.py and confirm the docstring explains the pattern

