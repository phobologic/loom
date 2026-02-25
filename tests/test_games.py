"""Tests for game creation, joining, and dashboard routes."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from loom.database import Base, get_db
from loom.main import _DEV_USERS, app
from loom.models import Game, GameMember, MemberRole, TieBreakingMethod, User
from loom.routers.games import MAX_GAME_PLAYERS

# Set by the client fixture; safe for serial test execution.
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
    """Log in as a specific user by ID."""
    await client.post("/dev/login", data={"user_id": str(user_id)}, follow_redirects=False)


async def _create_game(client: AsyncClient, name: str = "Test Game", pitch: str = "") -> int:
    """Create a game as the currently logged-in user; return game id."""
    response = await client.post(
        "/games", data={"name": name, "pitch": pitch}, follow_redirects=False
    )
    assert response.status_code == 303
    location = response.headers["location"]
    # location is /games/{id}
    return int(location.rsplit("/", 1)[-1])


class TestCreateGame:
    async def test_redirects_to_dashboard(self, client: AsyncClient) -> None:
        await _login(client, 1)
        response = await client.post("/games", data={"name": "My Game"}, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"].startswith("/games/")

    async def test_sets_organizer_role(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        async with _test_session_factory() as db:
            result = await db.execute(
                select(GameMember).where(
                    GameMember.game_id == game_id,
                    GameMember.user_id == 1,
                )
            )
            member = result.scalar_one()
        assert member.role == MemberRole.organizer

    async def test_generates_invite_token(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            game = result.scalar_one()
        assert game.invite_token is not None
        assert len(game.invite_token) > 0

    async def test_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post("/games", data={"name": "x"}, follow_redirects=False)
        assert response.status_code == 302
        assert "/dev/login" in response.headers["location"]


class TestGameDashboard:
    async def test_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/games/1", follow_redirects=False)
        assert response.status_code == 302
        assert "/dev/login" in response.headers["location"]

    async def test_requires_membership(self, client: AsyncClient) -> None:
        # User 1 creates the game
        await _login(client, 1)
        game_id = await _create_game(client)
        # Log out and log in as user 2 (not a member)
        await client.post("/dev/logout", follow_redirects=False)
        await _login(client, 2)
        response = await client.get(f"/games/{game_id}")
        assert response.status_code == 403

    async def test_shows_game_name(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client, name="Epic Adventure")
        response = await client.get(f"/games/{game_id}")
        assert response.status_code == 200
        assert "Epic Adventure" in response.text

    async def test_shows_members(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        response = await client.get(f"/games/{game_id}")
        assert response.status_code == 200
        assert "organizer" in response.text

    async def test_shows_invite_url_to_organizer(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        response = await client.get(f"/games/{game_id}")
        assert response.status_code == 200
        assert "/invite/" in response.text

    async def test_returns_404_for_missing_game(self, client: AsyncClient) -> None:
        await _login(client, 1)
        response = await client.get("/games/99999")
        assert response.status_code == 404


class TestInviteLanding:
    async def test_shows_game_name(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client, name="Dragon Quest")
        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            game = result.scalar_one()
        # Log out so we're not auto-redirected as an existing member
        await client.post("/dev/logout", follow_redirects=False)
        response = await client.get(f"/invite/{game.invite_token}")
        assert response.status_code == 200
        assert "Dragon Quest" in response.text

    async def test_invalid_token_shows_error(self, client: AsyncClient) -> None:
        response = await client.get("/invite/not-a-real-token")
        assert response.status_code == 200
        assert "invalid" in response.text.lower() or "revoked" in response.text.lower()

    async def test_already_member_redirects_to_dashboard(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            game = result.scalar_one()
        response = await client.get(f"/invite/{game.invite_token}", follow_redirects=False)
        assert response.status_code == 303
        assert f"/games/{game_id}" in response.headers["location"]


class TestJoinGame:
    async def test_join_via_invite(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            game = result.scalar_one()
        token = game.invite_token

        # Log in as user 2 and join
        await client.post("/dev/logout", follow_redirects=False)
        await _login(client, 2)
        response = await client.post(f"/invite/{token}", follow_redirects=False)
        assert response.status_code == 303
        assert f"/games/{game_id}" in response.headers["location"]

        # Verify membership
        async with _test_session_factory() as db:
            result = await db.execute(
                select(GameMember).where(
                    GameMember.game_id == game_id,
                    GameMember.user_id == 2,
                )
            )
            member = result.scalar_one()
        assert member.role == MemberRole.player

    async def test_join_already_member_redirects(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            game = result.scalar_one()
        token = game.invite_token

        await client.post("/dev/logout", follow_redirects=False)
        await _login(client, 2)
        await client.post(f"/invite/{token}", follow_redirects=False)
        # Join again
        response = await client.post(f"/invite/{token}", follow_redirects=False)
        assert response.status_code == 303

    async def test_join_enforces_player_cap(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            game = result.scalar_one()
        token = game.invite_token

        # Add members to fill the game
        async with _test_session_factory() as db:
            for extra_id in range(2, MAX_GAME_PLAYERS + 1):
                # Make sure the user exists
                result = await db.execute(select(User).where(User.id == extra_id))
                if result.scalar_one_or_none() is None:
                    db.add(User(id=extra_id, display_name=f"Extra{extra_id}"))
                    await db.flush()
                db.add(GameMember(game_id=game_id, user_id=extra_id, role=MemberRole.player))
            await db.commit()

        # Now try to join as user MAX_GAME_PLAYERS + 1 — game should be full
        # Use a fresh user that doesn't exist yet
        async with _test_session_factory() as db:
            overflow_user = User(display_name="Overflow")
            db.add(overflow_user)
            await db.commit()
            overflow_id = overflow_user.id

        await client.post("/dev/logout", follow_redirects=False)
        await client.post("/dev/login", data={"user_id": str(overflow_id)}, follow_redirects=False)
        response = await client.post(f"/invite/{token}", follow_redirects=False)
        assert response.status_code == 409

    async def test_join_invalid_token_returns_error(self, client: AsyncClient) -> None:
        await _login(client, 1)
        response = await client.post("/invite/not-valid", follow_redirects=False)
        assert response.status_code == 404


class TestInviteManagement:
    async def test_regenerate_invite_changes_token(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            original_token = result.scalar_one().invite_token

        response = await client.post(f"/games/{game_id}/invite/regenerate", follow_redirects=False)
        assert response.status_code == 303

        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            new_token = result.scalar_one().invite_token
        assert new_token != original_token
        assert new_token is not None

    async def test_regenerate_requires_organizer(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            token = result.scalar_one().invite_token

        # Join as user 2 (player role)
        await client.post("/dev/logout", follow_redirects=False)
        await _login(client, 2)
        await client.post(f"/invite/{token}", follow_redirects=False)

        response = await client.post(f"/games/{game_id}/invite/regenerate", follow_redirects=False)
        assert response.status_code == 403

    async def test_revoke_invite_clears_token(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        response = await client.post(f"/games/{game_id}/invite/revoke", follow_redirects=False)
        assert response.status_code == 303

        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            game = result.scalar_one()
        assert game.invite_token is None


class TestGameSettings:
    async def test_settings_requires_auth(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await client.post("/dev/logout", follow_redirects=False)
        response = await client.get(f"/games/{game_id}/settings", follow_redirects=False)
        assert response.status_code == 302
        assert "/dev/login" in response.headers["location"]

    async def test_settings_requires_membership(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await client.post("/dev/logout", follow_redirects=False)
        await _login(client, 2)
        response = await client.get(f"/games/{game_id}/settings")
        assert response.status_code == 403

    async def test_settings_page_loads_for_organizer(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        response = await client.get(f"/games/{game_id}/settings")
        assert response.status_code == 200
        assert "silence" in response.text.lower()
        assert "Save settings" in response.text

    async def test_player_can_view_settings(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            token = result.scalar_one().invite_token
        await client.post("/dev/logout", follow_redirects=False)
        await _login(client, 2)
        await client.post(f"/invite/{token}", follow_redirects=False)
        response = await client.get(f"/games/{game_id}/settings")
        assert response.status_code == 200
        assert "silence" in response.text.lower()
        assert "Save settings" not in response.text

    async def test_organizer_can_update_settings(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        response = await client.post(
            f"/games/{game_id}/settings",
            data={
                "silence_timer_hours": "24",
                "tie_breaking_method": "proposer",
                "beat_significance_threshold": "flag_most",
                "max_consecutive_beats": "5",
                "auto_generate_narrative": "",
                "fortune_roll_contest_window_hours": "6",
                "starting_tension": "7",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert f"/games/{game_id}/settings" in response.headers["location"]

        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            game = result.scalar_one()
        assert game.silence_timer_hours == 24
        assert game.tie_breaking_method == TieBreakingMethod.proposer
        assert game.auto_generate_narrative is False
        assert game.fortune_roll_contest_window_hours == 6
        assert game.starting_tension == 7

    async def test_player_cannot_update_settings(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            token = result.scalar_one().invite_token
        await client.post("/dev/logout", follow_redirects=False)
        await _login(client, 2)
        await client.post(f"/invite/{token}", follow_redirects=False)
        response = await client.post(
            f"/games/{game_id}/settings",
            data={"silence_timer_hours": "24"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_settings_returns_404_for_missing_game(self, client: AsyncClient) -> None:
        await _login(client, 1)
        response = await client.get("/games/99999/settings")
        assert response.status_code == 404


class TestInviteManagementRevoke:
    async def test_revoke_requires_organizer(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            token = result.scalar_one().invite_token

        # Join as user 2 (player)
        await client.post("/dev/logout", follow_redirects=False)
        await _login(client, 2)
        await client.post(f"/invite/{token}", follow_redirects=False)

        response = await client.post(f"/games/{game_id}/invite/revoke", follow_redirects=False)
        assert response.status_code == 403
