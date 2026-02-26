"""Tests for Step 22: In-App Notifications."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from loom.database import Base, get_db
from loom.main import _DEV_USERS, app
from loom.models import (
    Act,
    ActStatus,
    Character,
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    Notification,
    NotificationType,
    Scene,
    SceneStatus,
    User,
)

_test_session_factory: async_sessionmaker | None = None


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


async def _create_two_player_active_game(client: AsyncClient) -> int:
    """Create a game with two members (Alice=1 organizer, Bob=2 player) in active status."""
    await _login(client, 1)
    r = await client.post(
        "/games", data={"name": "Test Game", "pitch": "A pitch"}, follow_redirects=False
    )
    game_id = int(r.headers["location"].rsplit("/", 1)[-1])

    async with _test_session_factory() as db:
        result = await db.execute(select(User).where(User.id == 2))
        bob = result.scalar_one()
        db.add(
            GameMember(
                game_id=game_id,
                user_id=bob.id,
                role=MemberRole.player,
            )
        )
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one()
        game.status = GameStatus.active
        await db.commit()

    return game_id


async def _create_active_scene(game_id: int) -> tuple[int, int]:
    """Insert an active act and scene; return (act_id, scene_id)."""
    async with _test_session_factory() as db:
        result = await db.execute(select(User).where(User.id == 1))
        alice = result.scalar_one()

        char = Character(game_id=game_id, owner_id=alice.id, name="Aria")
        db.add(char)
        await db.flush()

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
            guiding_question="What happens here?",
            tension=5,
            status=SceneStatus.active,
            order=1,
        )
        db.add(scene)
        await db.flush()
        await db.refresh(scene, ["characters_present"])
        scene.characters_present = [char]
        await db.commit()

        return act.id, scene.id


async def _get_notifications(user_id: int) -> list[Notification]:
    async with _test_session_factory() as db:
        result = await db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at)
        )
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Tests — notification helper
# ---------------------------------------------------------------------------


async def test_new_beat_notifies_other_members(client: AsyncClient):
    """Submitting a beat creates a new_beat notification for all other game members."""
    game_id = await _create_two_player_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    await _login(client, 1)
    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
        data={
            "event_type": ["narrative"],
            "event_content": ["Alice does something dramatic."],
            "event_notation": [""],
            "event_reason": [""],
            "beat_significance": "minor",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    # Alice (submitter) should NOT get a notification
    alice_notifs = await _get_notifications(user_id=1)
    assert not any(n.notification_type == NotificationType.new_beat for n in alice_notifs)

    # Bob (other member) SHOULD get a new_beat notification
    bob_notifs = await _get_notifications(user_id=2)
    new_beat_notifs = [n for n in bob_notifs if n.notification_type == NotificationType.new_beat]
    assert len(new_beat_notifs) == 1
    assert new_beat_notifs[0].game_id == game_id
    assert new_beat_notifs[0].read_at is None


async def test_major_beat_creates_vote_required_notification(client: AsyncClient):
    """Submitting a major beat creates a vote_required notification for other members."""
    game_id = await _create_two_player_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    await _login(client, 1)
    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
        data={
            "event_type": ["narrative"],
            "event_content": ["A major event occurs."],
            "event_notation": [""],
            "event_reason": [""],
            "beat_significance": "major",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    bob_notifs = await _get_notifications(user_id=2)
    vote_notifs = [n for n in bob_notifs if n.notification_type == NotificationType.vote_required]
    assert len(vote_notifs) == 1


async def test_notifications_view_lists_user_notifications(client: AsyncClient):
    """GET /notifications returns the notifications page for the logged-in user."""
    game_id = await _create_two_player_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    await _login(client, 1)
    await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
        data={
            "event_type": ["narrative"],
            "event_content": ["Something happens."],
            "event_notation": [""],
            "event_reason": [""],
            "beat_significance": "minor",
        },
        follow_redirects=False,
    )

    # Bob views his notifications
    await _login(client, 2)
    r = await client.get("/notifications")
    assert r.status_code == 200
    assert "A new beat was submitted" in r.text


async def test_mark_notification_read(client: AsyncClient):
    """POST /notifications/{id}/read marks a notification as read."""
    game_id = await _create_two_player_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    await _login(client, 1)
    await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
        data={
            "event_type": ["narrative"],
            "event_content": ["Something happens."],
            "event_notation": [""],
            "event_reason": [""],
            "beat_significance": "minor",
        },
        follow_redirects=False,
    )

    bob_notifs = await _get_notifications(user_id=2)
    assert bob_notifs
    notif_id = bob_notifs[0].id

    await _login(client, 2)
    r = await client.post(f"/notifications/{notif_id}/read", follow_redirects=False)
    assert r.status_code == 302

    updated = await _get_notifications(user_id=2)
    assert updated[0].read_at is not None


async def test_mark_all_read(client: AsyncClient):
    """POST /notifications/read-all marks all unread notifications as read."""
    game_id = await _create_two_player_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    # Submit two beats to create two notifications for Bob
    await _login(client, 1)
    for content in ["Beat one.", "Beat two."]:
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={
                "event_type": ["narrative"],
                "event_content": [content],
                "event_notation": [""],
                "event_reason": [""],
                "beat_significance": "minor",
            },
            follow_redirects=False,
        )

    bob_notifs = await _get_notifications(user_id=2)
    assert len(bob_notifs) >= 2
    assert all(n.read_at is None for n in bob_notifs)

    await _login(client, 2)
    r = await client.post("/notifications/read-all", follow_redirects=False)
    assert r.status_code == 302

    updated = await _get_notifications(user_id=2)
    assert all(n.read_at is not None for n in updated)


async def test_notifications_not_visible_to_other_users(client: AsyncClient):
    """A user cannot read another user's notifications."""
    game_id = await _create_two_player_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    # Alice submits a beat → Bob gets a notification
    await _login(client, 1)
    await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
        data={
            "event_type": ["narrative"],
            "event_content": ["Something."],
            "event_notation": [""],
            "event_reason": [""],
            "beat_significance": "minor",
        },
        follow_redirects=False,
    )

    bob_notifs = await _get_notifications(user_id=2)
    notif_id = bob_notifs[0].id

    # Alice tries to mark Bob's notification as read — should 404
    r = await client.post(f"/notifications/{notif_id}/read", follow_redirects=False)
    assert r.status_code == 404


async def test_unread_count_endpoint(client: AsyncClient):
    """GET /notifications/unread-count returns correct JSON count."""
    game_id = await _create_two_player_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    await _login(client, 1)
    await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
        data={
            "event_type": ["narrative"],
            "event_content": ["Something."],
            "event_notation": [""],
            "event_reason": [""],
            "beat_significance": "minor",
        },
        follow_redirects=False,
    )

    await _login(client, 2)
    r = await client.get("/notifications/unread-count")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1

    # Scoped to the game
    r2 = await client.get(f"/notifications/unread-count?game_id={game_id}")
    assert r2.status_code == 200
    assert r2.json()["count"] >= 1


async def test_games_list_shows_unread_counts(client: AsyncClient):
    """GET /games shows unread notification counts per game."""
    game_id = await _create_two_player_active_game(client)
    act_id, scene_id = await _create_active_scene(game_id)

    await _login(client, 1)
    await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
        data={
            "event_type": ["narrative"],
            "event_content": ["Something."],
            "event_notation": [""],
            "event_reason": [""],
            "beat_significance": "minor",
        },
        follow_redirects=False,
    )

    await _login(client, 2)
    r = await client.get("/games")
    assert r.status_code == 200
    assert "new]" in r.text or "unread" in r.text


async def test_act_proposal_creates_vote_required_notification(client: AsyncClient):
    """Proposing an act in a multi-player game creates vote_required for other members."""
    game_id = await _create_two_player_active_game(client)

    await _login(client, 1)
    r = await client.post(
        f"/games/{game_id}/acts",
        data={"guiding_question": "What is at stake?", "title": ""},
        follow_redirects=False,
    )
    assert r.status_code == 303

    bob_notifs = await _get_notifications(user_id=2)
    vote_notifs = [n for n in bob_notifs if n.notification_type == NotificationType.vote_required]
    assert len(vote_notifs) == 1
    assert "act proposal" in vote_notifs[0].message
