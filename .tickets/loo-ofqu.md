---
id: loo-ofqu
status: open
deps: []
links: []
created: 2026-02-27T00:04:28Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-82fd
---
# Add shared client and db fixtures to conftest.py

Extract the new savepoint-based fixtures into conftest.py so every test file can use them without defining its own engine setup.

## Background
test_auth.py was already migrated as a pilot (see commit history). Its client fixture now lives locally in test_auth.py — this ticket moves it to conftest.py and adds the companion db fixture.

db_engine (module-scoped, StaticPool) is already in conftest.py from the pilot.

## Work required

### 1. Move client fixture to conftest.py
Move the client fixture from tests/test_auth.py to tests/conftest.py and remove it from test_auth.py (the conftest version will be found automatically).

The fixture:
```python
@pytest_asyncio.fixture(loop_scope="module")
async def client(db_engine):
    async with db_engine.connect() as conn:
        await conn.begin()
        async with AsyncSession(bind=conn, join_transaction_mode="create_savepoint") as setup:
            for name in _DEV_USERS:
                setup.add(User(display_name=name))
            await setup.commit()

        async def override_get_db():
            async with AsyncSession(
                bind=conn, join_transaction_mode="create_savepoint"
            ) as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
        app.dependency_overrides.pop(get_db, None)
        await conn.rollback()
```

### 2. Add db fixture to conftest.py
Tests that assert DB state after HTTP requests need direct session access. Add:

```python
@pytest_asyncio.fixture(loop_scope="module")
async def db(db_engine):
    async with db_engine.connect() as conn:
        await conn.begin()
        async with AsyncSession(bind=conn, join_transaction_mode="create_savepoint") as session:
            yield session
        await conn.rollback()
```

Wait — this won't work as-is because client and db need to share the same connection to see each other's writes. The correct design is a shared db_conn fixture:

```python
@pytest_asyncio.fixture(loop_scope="module")
async def db_conn(db_engine):
    """Per-test connection with an open outer transaction. Rolled back on teardown."""
    async with db_engine.connect() as conn:
        await conn.begin()
        # Seed dev users inside the transaction (rolled back with everything else)
        async with AsyncSession(bind=conn, join_transaction_mode="create_savepoint") as setup:
            for name in _DEV_USERS:
                setup.add(User(display_name=name))
            await setup.commit()
        yield conn
        await conn.rollback()

@pytest_asyncio.fixture(loop_scope="module")
async def client(db_conn):
    async def override_get_db():
        async with AsyncSession(
            bind=db_conn, join_transaction_mode="create_savepoint"
        ) as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)

@pytest_asyncio.fixture(loop_scope="module")
async def db(db_conn):
    """Direct DB session sharing the same transaction as client."""
    async with AsyncSession(bind=db_conn, join_transaction_mode="create_savepoint") as session:
        yield session
```

Tests that only need HTTP use client. Tests needing both request both:
  async def test_foo(client, db): ...

### 3. Add module docstring to conftest.py
Explain the three-fixture design, StaticPool rationale, and rollback guarantee.

## Verification — measure the speedup
Before making changes, record a baseline:
  time uv run pytest -v tests/test_auth.py

After moving the fixture to conftest.py and confirming test_auth.py still passes:
  time uv run pytest -v tests/test_auth.py

The test time should be the same (already fast). Then run:
  uv run pytest -q --tb=short

All 360 tests should pass. This ticket is the foundation for all subsequent migration tickets.

