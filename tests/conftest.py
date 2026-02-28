"""Shared test fixtures for the loom test suite.

Three-fixture design for DB-integrated tests
---------------------------------------------
db_engine  (module scope)
    Creates the SQLite schema once per test module. Uses StaticPool so all
    logical connections share the same in-memory database.

db_conn  (function scope)
    Opens a connection, begins an outer transaction, and seeds the dev users
    (Alice, Bob, Charlie) inside a savepoint. After each test it rolls back the
    outer transaction, undoing both the seeded users and any writes made during
    the test. Schema is left intact for the next test.

client  (function scope)
    Builds an AsyncClient wired to the FastAPI app. Overrides get_db so every
    request uses the same connection as db_conn, participating in the same
    outer transaction via savepoints. Cleans up the override after the test.

db  (function scope)
    An AsyncSession on the same connection as client. Use this when a test
    needs to assert DB state that was written by an HTTP request.

For tests with no HTTP layer, db_conn or db can be used directly.
For tests with no DB at all (dice, AI context), no fixture is needed.
"""

from __future__ import annotations

import unittest.mock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from loom.ai.provider import AnthropicProvider
from loom.database import Base, get_db
from loom.main import _DEV_USERS, app
from loom.models import User


@pytest.fixture(autouse=True, scope="session")
def block_real_ai():
    """Fail fast if any test reaches the real Anthropic API provider.

    This is a hard stop independent of .env — if a mock is missing, the test
    gets a clear RuntimeError rather than a slow API call or an auth failure.
    """

    async def _blocked(*args, **kwargs):
        raise RuntimeError(
            "Real Anthropic API call attempted in tests — "
            "add a mock for this function in conftest.mock_ai"
        )

    with unittest.mock.patch.object(AnthropicProvider, "generate_structured", new=_blocked):
        yield


@pytest.fixture(autouse=True)
def mock_ai(monkeypatch):
    """Stub all AI client calls so tests never hit the Anthropic API."""

    async def _oracle_interpretations(
        question, word_pair, *, game=None, scene=None, db=None, game_id=None
    ):
        return [
            "The threads of fate suggest an unexpected alliance forms in shadow.",
            "Ancient obligations resurface, demanding a choice between duty and desire.",
            "What was lost cannot be reclaimed unchanged — but transformation awaits.",
        ]

    async def _session0_synthesis(
        question, inputs, *, game_name="", pitch="", db=None, game_id=None
    ):
        return (
            "A world of flickering gaslight and forgotten gods, where the streets whisper "
            "secrets and every alliance carries a hidden price."
        )

    async def _generate_world_document(session0_data, *, db=None, game_id=None):
        return "# World Document\n\nThis world is shaped by the choices made at its founding..."

    async def _check_beat_consistency(
        game, scene, beat_text, roll_results=None, *, db=None, game_id=None
    ):
        return []

    async def _expand_beat_prose(game, scene, beat_text, *, db=None, game_id=None):
        return None

    async def _suggest_character_updates(game, scene, character, *, db=None, game_id=None):
        return []

    async def _suggest_world_entries(
        beat_text, existing_entries, *, game=None, db=None, game_id=None
    ):
        return []

    async def _suggest_relationships(
        beat_text,
        characters,
        npcs,
        world_entries,
        existing_relationship_labels,
        *,
        game=None,
        db=None,
        game_id=None,
    ):
        return []

    async def _suggest_npc_details(
        beat_text,
        role,
        *,
        name=None,
        want=None,
        existing_pc_names=None,
        existing_npc_names=None,
        game=None,
        db=None,
        game_id=None,
    ):
        return ([], [])

    monkeypatch.setattr("loom.ai.client.oracle_interpretations", _oracle_interpretations)
    monkeypatch.setattr("loom.ai.client.session0_synthesis", _session0_synthesis)
    monkeypatch.setattr("loom.ai.client.generate_world_document", _generate_world_document)
    monkeypatch.setattr("loom.ai.client.check_beat_consistency", _check_beat_consistency)
    monkeypatch.setattr("loom.routers.scenes.check_beat_consistency", _check_beat_consistency)
    monkeypatch.setattr("loom.ai.client.expand_beat_prose", _expand_beat_prose)
    monkeypatch.setattr("loom.routers.scenes.expand_beat_prose", _expand_beat_prose)
    monkeypatch.setattr("loom.ai.client.suggest_character_updates", _suggest_character_updates)
    monkeypatch.setattr(
        "loom.routers.world_document._ai_suggest_character_updates", _suggest_character_updates
    )
    monkeypatch.setattr("loom.ai.client.suggest_npc_details", _suggest_npc_details)
    monkeypatch.setattr("loom.routers.npcs.suggest_npc_details", _suggest_npc_details)
    monkeypatch.setattr("loom.ai.client.suggest_world_entries", _suggest_world_entries)
    monkeypatch.setattr(
        "loom.routers.world_entries._ai_suggest_world_entries", _suggest_world_entries
    )
    monkeypatch.setattr("loom.ai.client.suggest_relationships", _suggest_relationships)
    monkeypatch.setattr(
        "loom.routers.relationships._ai_suggest_relationships", _suggest_relationships
    )

    # Also patch the imported names in the routers so the monkeypatches take effect
    monkeypatch.setattr("loom.routers.oracles.ai_oracle_interpretations", _oracle_interpretations)
    monkeypatch.setattr("loom.routers.session0.session0_synthesis", _session0_synthesis)
    monkeypatch.setattr(
        "loom.routers.world_document._ai_generate_world_document", _generate_world_document
    )


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def db_engine():
    """Module-scoped SQLite engine with schema created once.

    Uses StaticPool so all logical connections share the same in-memory
    database. Each test rolls back its own transaction for isolation.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="module")
async def db_conn(db_engine):
    """Per-test connection with a transaction that rolls back after each test.

    Seeds dev users within a savepoint so they're available to every test,
    then rolls back the outer transaction after the test to undo all writes.
    """
    async with db_engine.connect() as conn:
        await conn.begin()

        async with AsyncSession(bind=conn, join_transaction_mode="create_savepoint") as setup:
            for name in _DEV_USERS:
                setup.add(User(display_name=name))
            await setup.commit()

        yield conn

        await conn.rollback()


@pytest_asyncio.fixture(loop_scope="module")
async def client(db_conn):
    """AsyncClient wired to the app with DB writes rolled back after each test."""

    async def override_get_db():
        async with AsyncSession(
            bind=db_conn,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        ) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture(loop_scope="module")
async def db(db_conn):
    """AsyncSession on the same connection as client.

    Use this when a test needs to assert DB state written by an HTTP request.
    """
    async with AsyncSession(
        bind=db_conn,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    ) as session:
        yield session


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
