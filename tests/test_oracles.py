"""Tests for oracle invocation routes."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from loom.database import Base, get_db
from loom.main import _DEV_USERS, app
from loom.models import (
    Act,
    ActStatus,
    Beat,
    BeatStatus,
    Event,
    EventType,
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    ProposalType,
    Scene,
    SceneStatus,
    VoteProposal,
)

_test_session_factory: async_sessionmaker | None = None


@pytest.fixture
async def client():
    global _test_session_factory
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    _test_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with _test_session_factory() as db:
        for name in _DEV_USERS:
            db.add(__import__("loom.models", fromlist=["User"]).User(display_name=name))
        await db.commit()

    async def override_get_db():
        async with _test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    _test_session_factory = None


async def _login(client: AsyncClient, user_id: int) -> None:
    await client.post("/dev/login", data={"user_id": str(user_id)}, follow_redirects=False)


async def _create_active_game(client: AsyncClient) -> int:
    await _login(client, 1)
    r = await client.post(
        "/games", data={"name": "Test Game", "pitch": "A pitch"}, follow_redirects=False
    )
    game_id = int(r.headers["location"].rsplit("/", 1)[-1])
    await client.post(f"/games/{game_id}/session0/propose-ready", follow_redirects=False)
    return game_id


async def _create_active_scene(game_id: int) -> tuple[int, int]:
    """Insert an active act and active scene, return (act_id, scene_id)."""
    async with _test_session_factory() as db:
        act = Act(
            game_id=game_id,
            guiding_question="What is at stake?",
            status=ActStatus.active,
            order=1,
        )
        db.add(act)
        await db.flush()

        scene = Scene(
            act_id=act.id,
            guiding_question="What happens next?",
            status=SceneStatus.active,
            order=1,
        )
        db.add(scene)
        await db.commit()
        return act.id, scene.id


@pytest.mark.asyncio
async def test_oracle_get_shows_word_pair(client: AsyncClient) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    await _login(client, 1)
    r = await client.get(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
        follow_redirects=False,
    )
    assert r.status_code == 200
    body = r.text
    assert "word_action" in body
    assert "word_descriptor" in body
    assert "Invoke Oracle" in body
    assert "Re-roll" in body


@pytest.mark.asyncio
async def test_oracle_post_creates_beat_and_event(client: AsyncClient) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    await _login(client, 1)
    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
        data={
            "question": "Will the alliance hold?",
            "word_action": "betray",
            "word_descriptor": "trust",
            "beat_significance": "minor",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    async with _test_session_factory() as db:
        result = await db.execute(
            select(Beat).where(Beat.scene_id == scene_id).options(selectinload(Beat.events))
        )
        beats = result.scalars().all()
        assert len(beats) == 1
        beat = beats[0]
        assert beat.status == BeatStatus.canon

        assert len(beat.events) == 1
        event = beat.events[0]
        assert event.type == EventType.oracle
        assert event.oracle_query == "Will the alliance hold?"
        assert event.word_seed_action == "betray"
        assert event.word_seed_descriptor == "trust"
        assert len(event.interpretations) == 3


@pytest.mark.asyncio
async def test_oracle_post_requires_active_scene(client: AsyncClient) -> None:
    game_id = await _create_active_game(client)

    async with _test_session_factory() as db:
        act = Act(
            game_id=game_id,
            guiding_question="Q",
            status=ActStatus.active,
            order=1,
        )
        db.add(act)
        await db.flush()
        scene = Scene(
            act_id=act.id,
            guiding_question="Q",
            status=SceneStatus.proposed,
            order=1,
        )
        db.add(scene)
        await db.commit()
        act_id, scene_id = act.id, scene.id

    await _login(client, 1)
    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
        data={
            "question": "What lies ahead?",
            "word_action": "reveal",
            "word_descriptor": "shadow",
        },
        follow_redirects=False,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_oracle_post_requires_question(client: AsyncClient) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    await _login(client, 1)
    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
        data={
            "question": "   ",
            "word_action": "reveal",
            "word_descriptor": "shadow",
        },
        follow_redirects=False,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_oracle_post_major_creates_proposal(client: AsyncClient) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    await _login(client, 1)
    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
        data={
            "question": "What is the cost?",
            "word_action": "sacrifice",
            "word_descriptor": "legacy",
            "beat_significance": "major",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    async with _test_session_factory() as db:
        result = await db.execute(
            select(VoteProposal).where(VoteProposal.proposal_type == ProposalType.beat_proposal)
        )
        proposals = result.scalars().all()
        assert len(proposals) == 1
