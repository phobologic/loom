import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from loom.database import Base
from loom.main import app


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

    monkeypatch.setattr("loom.ai.client.oracle_interpretations", _oracle_interpretations)
    monkeypatch.setattr("loom.ai.client.session0_synthesis", _session0_synthesis)
    monkeypatch.setattr("loom.ai.client.generate_world_document", _generate_world_document)
    monkeypatch.setattr("loom.ai.client.check_beat_consistency", _check_beat_consistency)
    monkeypatch.setattr("loom.routers.scenes.check_beat_consistency", _check_beat_consistency)

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


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
