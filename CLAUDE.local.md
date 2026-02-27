# loom — Local Conventions

## Design Principles (push back if violated)

loom has named design principles in `planning/requirements.md` → Key Design Principles.
**Read that section before planning any feature.** When a ticket, spec, or user request
proposes something that conflicts with these principles — even subtly — raise it before
implementing. Don't just build what's asked.

Red flags to catch:

- A vote or majority decision that can **override already-canon player contributions** →
  violates "Author authority on canon". Challenge resolution is discussion + author decides,
  not a vote that forces a change.

- A **hard block** on player action where a nudge or suggestion would do →
  violates "Nudges over mandates". Prefer "you've posted 3 beats, maybe let others in?"
  over "you cannot post a fourth beat."

- **AI output becoming canon without player confirmation** → violates "AI assists, players
  decide". AI generates options; players choose.

- **Organizer getting narrative shortcuts** (approve stuck proposals, skip a challenge on
  their own game, override a vote) → violates "Organizer has no narrative privilege."

- **Adversarial framing** in collaborative features — voting to "defeat" someone else's
  content, challenge mechanisms that feel like accusations rather than conversations.

When you catch one: name the principle, explain the conflict, and propose an alternative
before proceeding.

## Testing Conventions

**Never create a per-test SQLite engine.** The `create_all` + seed + `drop_all` pattern
costs ~71ms per test and compounds to minutes at scale.

Use the shared fixtures from `tests/conftest.py` instead:

| Fixture | What it gives you |
|---------|------------------|
| `client` | `AsyncClient` connected to the app; DB seeded with dev users; all writes rolled back after the test |
| `db` | `AsyncSession` on the same transaction as `client` — use when you need to assert DB state after an HTTP request |

```python
# WRONG — never do this
@pytest.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)   # ← slow, runs per test
    ...

# RIGHT — just request the fixture
async def test_create_game(client, db):
    response = await client.post("/games", data={"name": "My Game"})
    assert response.status_code == 303
    game = await db.scalar(select(Game).where(Game.name == "My Game"))
    assert game is not None
```

For pure unit tests with no HTTP layer, `db` can be used alone. For tests with no DB
at all (dice, AI context), no fixture is needed.

The fixtures use `StaticPool` + per-test transaction rollback (SQLite savepoints).
Schema is created once per module. See `tests/conftest.py` for implementation.

## Alembic Migrations

**Always verify the current head before writing a new migration.** Run `uv run alembic heads`
first — the output must show a single head revision. Use that hash as `down_revision` in the
new file. Never copy a parent hash from an existing migration file without checking, as another
migration may already have extended that revision, creating a branch.
