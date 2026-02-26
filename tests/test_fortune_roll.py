"""Tests for Fortune Roll — probability engine and HTTP routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from loom.database import Base, get_db
from loom.fortune_roll import (
    FORTUNE_ROLL_ODDS,
    compute_fortune_roll_result,
    fortune_roll_contest_window_hours,
    is_exceptional,
)
from loom.main import _DEV_USERS, app
from loom.models import (
    Act,
    ActStatus,
    Beat,
    BeatSignificance,
    BeatStatus,
    Event,
    EventType,
    Game,
    GameStatus,
    ProposalType,
    Scene,
    SceneStatus,
    User,
    VoteProposal,
)

_test_session_factory: async_sessionmaker | None = None


# ---------------------------------------------------------------------------
# Unit tests — fortune_roll module
# ---------------------------------------------------------------------------


def test_compute_fortune_roll_valid_odds():
    """All valid odds values can be rolled without error."""
    for odds in FORTUNE_ROLL_ODDS:
        result = compute_fortune_roll_result(odds, 5)
        assert result in ("exceptional_yes", "yes", "no", "exceptional_no")


def test_compute_fortune_roll_clamps_tension():
    """Out-of-range tension is clamped rather than raising."""
    r1 = compute_fortune_roll_result("fifty_fifty", 0)
    r2 = compute_fortune_roll_result("fifty_fifty", 10)
    assert r1 in ("exceptional_yes", "yes", "no", "exceptional_no")
    assert r2 in ("exceptional_yes", "yes", "no", "exceptional_no")


def test_compute_fortune_roll_invalid_odds():
    with pytest.raises(ValueError, match="Invalid odds"):
        compute_fortune_roll_result("garbage", 5)


def test_compute_fortune_roll_deterministic(monkeypatch):
    """A roll of 0 always gives exceptional_yes for a near_certain odds."""
    with patch("loom.fortune_roll.random.randint", return_value=0):
        result = compute_fortune_roll_result("near_certain", 5)
    assert result == "exceptional_yes"


def test_compute_fortune_roll_exceptional_no(monkeypatch):
    """A roll of 99 always gives exceptional_no for impossible odds."""
    with patch("loom.fortune_roll.random.randint", return_value=99):
        result = compute_fortune_roll_result("impossible", 5)
    assert result == "exceptional_no"


def test_is_exceptional():
    assert is_exceptional("exceptional_yes") is True
    assert is_exceptional("exceptional_no") is True
    assert is_exceptional("yes") is False
    assert is_exceptional("no") is False


def test_fortune_roll_contest_window_default():
    assert fortune_roll_contest_window_hours(12, None) == 6
    assert fortune_roll_contest_window_hours(1, None) == 1  # max(1, 0) = 1


def test_fortune_roll_contest_window_override():
    assert fortune_roll_contest_window_hours(12, 4) == 4


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    global _test_session_factory
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    _test_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with _test_session_factory() as db:
        for name in _DEV_USERS:
            db.add(User(display_name=name))
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
    """Insert an active act and active scene; return (act_id, scene_id)."""
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
            tension=5,
            order=1,
        )
        db.add(scene)
        await db.commit()
        return act.id, scene.id


# ---------------------------------------------------------------------------
# Integration tests — HTTP routes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fortune_roll_form_requires_active_scene(client: AsyncClient):
    """GET fortune roll returns 403 for an inactive scene."""
    game_id = await _create_active_game(client)
    async with _test_session_factory() as db:
        act = Act(
            game_id=game_id,
            guiding_question="Q?",
            status=ActStatus.active,
            order=1,
        )
        db.add(act)
        await db.flush()
        scene = Scene(
            act_id=act.id,
            guiding_question="Q?",
            status=SceneStatus.proposed,
            tension=5,
            order=1,
        )
        db.add(scene)
        await db.commit()
        act_id, scene_id = act.id, scene.id

    r = await client.get(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/fortune-roll",
        follow_redirects=False,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_fortune_roll_form_returns_200(client: AsyncClient):
    """GET fortune roll form renders for an active scene."""
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    r = await client.get(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/fortune-roll",
        follow_redirects=False,
    )
    assert r.status_code == 200
    assert b"Fortune Roll" in r.content
    assert b"fifty_fifty" in r.content or b"50/50" in r.content


@pytest.mark.asyncio
async def test_fortune_roll_post_creates_pending_event(client: AsyncClient):
    """POST creates a beat+event with result=None and an expiry deadline."""
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/fortune-roll",
        data={"question": "Will it work?", "odds": "likely"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    async with _test_session_factory() as db:
        result = await db.execute(
            select(Event)
            .join(Beat)
            .join(Scene)
            .where(Scene.id == scene_id)
            .where(Event.type == EventType.fortune_roll)
        )
        event = result.scalar_one()

    assert event.oracle_query == "Will it work?"
    assert event.fortune_roll_odds == "likely"
    assert event.fortune_roll_result is None
    assert event.fortune_roll_expires_at is not None
    assert event.fortune_roll_tension == 5
    assert event.fortune_roll_contested is False


@pytest.mark.asyncio
async def test_fortune_roll_post_invalid_odds(client: AsyncClient):
    """POST with invalid odds returns 422."""
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/fortune-roll",
        data={"question": "Will it work?", "odds": "maybe"},
        follow_redirects=False,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_fortune_roll_post_empty_question(client: AsyncClient):
    """POST with empty question returns 422."""
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/fortune-roll",
        data={"question": "   ", "odds": "fifty_fifty"},
        follow_redirects=False,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_fortune_roll_non_member_rejected(client: AsyncClient):
    """Non-members cannot submit a Fortune Roll."""
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    # Log in as user 2 who is not a member
    await _login(client, 2)
    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/fortune-roll",
        data={"question": "Will it?", "odds": "fifty_fifty"},
        follow_redirects=False,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_fortune_roll_auto_resolves_on_scene_view(client: AsyncClient):
    """A pending Fortune Roll with an expired contest window resolves on scene view."""
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    # Create a pending fortune roll with an already-expired deadline
    async with _test_session_factory() as db:
        beat = Beat(
            scene_id=scene_id,
            author_id=1,
            significance=BeatSignificance.minor,
            status=BeatStatus.proposed,
            order=1,
        )
        db.add(beat)
        await db.flush()
        event = Event(
            beat_id=beat.id,
            type=EventType.fortune_roll,
            oracle_query="Does this resolve?",
            fortune_roll_odds="fifty_fifty",
            fortune_roll_tension=5,
            fortune_roll_result=None,
            fortune_roll_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            fortune_roll_contested=False,
            order=1,
        )
        db.add(event)
        await db.commit()
        event_id = event.id

    # Load the scene — auto-resolution should fire
    r = await client.get(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}",
        follow_redirects=False,
    )
    assert r.status_code == 200

    async with _test_session_factory() as db:
        refreshed = await db.get(Event, event_id)

    assert refreshed.fortune_roll_result is not None
    assert refreshed.fortune_roll_result in ("exceptional_yes", "yes", "no", "exceptional_no")


@pytest.mark.asyncio
async def test_fortune_roll_not_auto_resolved_before_window(client: AsyncClient):
    """A pending Fortune Roll within its contest window does NOT auto-resolve."""
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    async with _test_session_factory() as db:
        beat = Beat(
            scene_id=scene_id,
            author_id=1,
            significance=BeatSignificance.minor,
            status=BeatStatus.proposed,
            order=1,
        )
        db.add(beat)
        await db.flush()
        event = Event(
            beat_id=beat.id,
            type=EventType.fortune_roll,
            oracle_query="Too soon?",
            fortune_roll_odds="fifty_fifty",
            fortune_roll_tension=5,
            fortune_roll_result=None,
            fortune_roll_expires_at=datetime.now(timezone.utc) + timedelta(hours=6),
            fortune_roll_contested=False,
            order=1,
        )
        db.add(event)
        await db.commit()
        event_id = event.id

    r = await client.get(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}",
        follow_redirects=False,
    )
    assert r.status_code == 200

    async with _test_session_factory() as db:
        refreshed = await db.get(Event, event_id)

    assert refreshed.fortune_roll_result is None


@pytest.mark.asyncio
async def test_fortune_roll_contest_blocks_auto_resolve(client: AsyncClient):
    """A contested Fortune Roll does NOT auto-resolve even after the window."""
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    async with _test_session_factory() as db:
        beat = Beat(
            scene_id=scene_id,
            author_id=1,
            significance=BeatSignificance.minor,
            status=BeatStatus.proposed,
            order=1,
        )
        db.add(beat)
        await db.flush()
        event = Event(
            beat_id=beat.id,
            type=EventType.fortune_roll,
            oracle_query="Contested?",
            fortune_roll_odds="fifty_fifty",
            fortune_roll_tension=5,
            fortune_roll_result=None,
            fortune_roll_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            fortune_roll_contested=True,  # contested!
            order=1,
        )
        db.add(event)
        await db.commit()
        event_id = event.id

    r = await client.get(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}",
        follow_redirects=False,
    )
    assert r.status_code == 200

    async with _test_session_factory() as db:
        refreshed = await db.get(Event, event_id)

    assert refreshed.fortune_roll_result is None


@pytest.mark.asyncio
async def test_fortune_roll_exceptional_creates_major_beat(client: AsyncClient):
    """An exceptional result upgrades the beat to major and creates a VoteProposal."""
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    async with _test_session_factory() as db:
        beat = Beat(
            scene_id=scene_id,
            author_id=1,
            significance=BeatSignificance.minor,
            status=BeatStatus.proposed,
            order=1,
        )
        db.add(beat)
        await db.flush()
        event = Event(
            beat_id=beat.id,
            type=EventType.fortune_roll,
            oracle_query="Drama incoming?",
            fortune_roll_odds="fifty_fifty",
            fortune_roll_tension=5,
            fortune_roll_result=None,
            fortune_roll_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            fortune_roll_contested=False,
            order=1,
        )
        db.add(event)
        await db.commit()
        beat_id = beat.id
        event_id = event.id

    # Force an exceptional result
    with patch("loom.fortune_roll.random.randint", return_value=0):
        r = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}",
            follow_redirects=False,
        )
    assert r.status_code == 200

    async with _test_session_factory() as db:
        refreshed_event = await db.get(Event, event_id)
        refreshed_beat = await db.get(Beat, beat_id)
        proposals = await db.execute(
            select(VoteProposal).where(
                VoteProposal.beat_id == beat_id,
                VoteProposal.proposal_type == ProposalType.beat_proposal,
            )
        )
        proposal = proposals.scalar_one_or_none()

    assert refreshed_event.fortune_roll_result == "exceptional_yes"
    assert refreshed_beat.significance == BeatSignificance.major
    assert proposal is not None


@pytest.mark.asyncio
async def test_fortune_roll_regular_result_minor_canon(client: AsyncClient):
    """A regular (non-exceptional) result keeps the beat as minor and marks it canon."""
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    async with _test_session_factory() as db:
        beat = Beat(
            scene_id=scene_id,
            author_id=1,
            significance=BeatSignificance.minor,
            status=BeatStatus.proposed,
            order=1,
        )
        db.add(beat)
        await db.flush()
        event = Event(
            beat_id=beat.id,
            type=EventType.fortune_roll,
            oracle_query="Routine?",
            fortune_roll_odds="fifty_fifty",
            fortune_roll_tension=5,
            fortune_roll_result=None,
            fortune_roll_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            fortune_roll_contested=False,
            order=1,
        )
        db.add(event)
        await db.commit()
        beat_id = beat.id
        event_id = event.id

    # Force a regular "yes" result (roll in range [A, B))
    # At fifty_fifty, tension 5: A=10, B=50. Roll=30 → "yes"
    with patch("loom.fortune_roll.random.randint", return_value=30):
        r = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}",
            follow_redirects=False,
        )
    assert r.status_code == 200

    async with _test_session_factory() as db:
        refreshed_event = await db.get(Event, event_id)
        refreshed_beat = await db.get(Beat, beat_id)

    assert refreshed_event.fortune_roll_result == "yes"
    assert refreshed_beat.significance == BeatSignificance.minor
    assert refreshed_beat.status == BeatStatus.canon


@pytest.mark.asyncio
async def test_contest_fortune_roll(client: AsyncClient):
    """A game member can contest a pending Fortune Roll."""
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    async with _test_session_factory() as db:
        beat = Beat(
            scene_id=scene_id,
            author_id=1,
            significance=BeatSignificance.minor,
            status=BeatStatus.proposed,
            order=1,
        )
        db.add(beat)
        await db.flush()
        event = Event(
            beat_id=beat.id,
            type=EventType.fortune_roll,
            oracle_query="Contestable?",
            fortune_roll_odds="likely",
            fortune_roll_tension=5,
            fortune_roll_result=None,
            fortune_roll_expires_at=datetime.now(timezone.utc) + timedelta(hours=6),
            fortune_roll_contested=False,
            order=1,
        )
        db.add(event)
        await db.commit()
        event_id = event.id

    r = await client.post(
        f"/games/{game_id}/fortune-roll/events/{event_id}/contest",
        follow_redirects=False,
    )
    assert r.status_code == 303

    async with _test_session_factory() as db:
        refreshed = await db.get(Event, event_id)
    assert refreshed.fortune_roll_contested is True


@pytest.mark.asyncio
async def test_reaffirm_fortune_roll(client: AsyncClient):
    """Invoker can reaffirm after a contest, resetting the window."""
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    old_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    async with _test_session_factory() as db:
        beat = Beat(
            scene_id=scene_id,
            author_id=1,
            significance=BeatSignificance.minor,
            status=BeatStatus.proposed,
            order=1,
        )
        db.add(beat)
        await db.flush()
        event = Event(
            beat_id=beat.id,
            type=EventType.fortune_roll,
            oracle_query="Reaffirm me",
            fortune_roll_odds="likely",
            fortune_roll_tension=5,
            fortune_roll_result=None,
            fortune_roll_expires_at=old_expiry,
            fortune_roll_contested=True,
            order=1,
        )
        db.add(event)
        await db.commit()
        event_id = event.id

    r = await client.post(
        f"/games/{game_id}/fortune-roll/events/{event_id}/reaffirm",
        follow_redirects=False,
    )
    assert r.status_code == 303

    async with _test_session_factory() as db:
        refreshed = await db.get(Event, event_id)

    assert refreshed.fortune_roll_contested is False
    # SQLite returns naive datetimes; strip tz from old_expiry for comparison
    old_expiry_naive = old_expiry.replace(tzinfo=None)
    assert refreshed.fortune_roll_expires_at > old_expiry_naive


@pytest.mark.asyncio
async def test_reaffirm_only_invoker(client: AsyncClient):
    """Only the invoker can reaffirm; non-invokers get 403."""
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    # Add user 2 as a member
    from loom.models import GameMember, MemberRole

    async with _test_session_factory() as db:
        db.add(GameMember(game_id=game_id, user_id=2, role=MemberRole.player))
        beat = Beat(
            scene_id=scene_id,
            author_id=1,
            significance=BeatSignificance.minor,
            status=BeatStatus.proposed,
            order=1,
        )
        db.add(beat)
        await db.flush()
        event = Event(
            beat_id=beat.id,
            type=EventType.fortune_roll,
            oracle_query="Who can reaffirm?",
            fortune_roll_odds="likely",
            fortune_roll_tension=5,
            fortune_roll_result=None,
            fortune_roll_expires_at=datetime.now(timezone.utc) + timedelta(hours=6),
            fortune_roll_contested=True,
            order=1,
        )
        db.add(event)
        await db.commit()
        event_id = event.id

    # User 2 (not the invoker) tries to reaffirm
    await _login(client, 2)
    r = await client.post(
        f"/games/{game_id}/fortune-roll/events/{event_id}/reaffirm",
        follow_redirects=False,
    )
    assert r.status_code == 403
