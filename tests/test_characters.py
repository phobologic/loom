"""Tests for character creation and management routes."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from loom.database import Base, get_db
from loom.main import _DEV_USERS, app
from loom.models import Character, Game, GameMember, GameStatus, MemberRole, User

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
    await client.post("/dev/login", data={"user_id": str(user_id)}, follow_redirects=False)


async def _create_game(client: AsyncClient, name: str = "Test Game") -> int:
    response = await client.post("/games", data={"name": name, "pitch": ""}, follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]
    return int(location.rsplit("/", 1)[-1])


async def _add_member(game_id: int, user_id: int, role: MemberRole = MemberRole.player) -> None:
    async with _test_session_factory() as db:
        db.add(GameMember(game_id=game_id, user_id=user_id, role=role))
        await db.commit()


async def _activate_game(game_id: int) -> None:
    """Set game status to active directly in DB."""
    async with _test_session_factory() as db:
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one()
        game.status = GameStatus.active
        await db.commit()


async def _get_characters(game_id: int) -> list[Character]:
    async with _test_session_factory() as db:
        result = await db.execute(
            select(Character).where(Character.game_id == game_id).order_by(Character.created_at)
        )
        return list(result.scalars().all())


class TestCharactersPage:
    async def _setup(self, client: AsyncClient) -> int:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(game_id)
        return game_id

    async def test_page_loads_for_member(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        response = await client.get(f"/games/{game_id}/characters")
        assert response.status_code == 200
        assert "Characters" in response.text

    async def test_page_requires_membership(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await _login(client, 2)
        response = await client.get(f"/games/{game_id}/characters")
        assert response.status_code == 403

    async def test_page_blocked_during_setup(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        # Game is in setup status — not activated
        response = await client.get(f"/games/{game_id}/characters")
        assert response.status_code == 403

    async def test_page_shows_create_form_when_no_character(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        response = await client.get(f"/games/{game_id}/characters")
        assert response.status_code == 200
        assert "Create Your Character" in response.text

    async def test_page_hides_create_form_when_has_character(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await client.post(
            f"/games/{game_id}/characters",
            data={"name": "Aria", "description": "", "notes": ""},
            follow_redirects=False,
        )
        response = await client.get(f"/games/{game_id}/characters")
        assert response.status_code == 200
        assert "Create Your Character" not in response.text
        assert "Aria" in response.text

    async def test_all_members_see_all_characters(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        # Alice creates her character
        await client.post(
            f"/games/{game_id}/characters",
            data={"name": "Aria", "description": "A scholar", "notes": ""},
            follow_redirects=False,
        )
        # Bob joins and creates his character
        await _add_member(game_id, 2)
        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/characters",
            data={"name": "Brennan", "description": "A warrior", "notes": ""},
            follow_redirects=False,
        )
        # Bob sees both characters
        response = await client.get(f"/games/{game_id}/characters")
        assert "Aria" in response.text
        assert "Brennan" in response.text

    async def test_page_requires_auth(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        client.cookies.clear()
        response = await client.get(f"/games/{game_id}/characters", follow_redirects=False)
        assert response.status_code in (302, 303)


class TestCreateCharacter:
    async def _setup(self, client: AsyncClient) -> int:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(game_id)
        return game_id

    async def test_create_succeeds(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        response = await client.post(
            f"/games/{game_id}/characters",
            data={"name": "Aria", "description": "A scholar of the old ways", "notes": "Curious"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        chars = await _get_characters(game_id)
        assert len(chars) == 1
        assert chars[0].name == "Aria"
        assert chars[0].description == "A scholar of the old ways"
        assert chars[0].notes == "Curious"

    async def test_create_with_name_only(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        response = await client.post(
            f"/games/{game_id}/characters",
            data={"name": "Sable", "description": "", "notes": ""},
            follow_redirects=False,
        )
        assert response.status_code == 303
        chars = await _get_characters(game_id)
        assert len(chars) == 1
        assert chars[0].name == "Sable"
        assert chars[0].description is None
        assert chars[0].notes is None

    async def test_one_character_per_player(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await client.post(
            f"/games/{game_id}/characters",
            data={"name": "First", "description": "", "notes": ""},
            follow_redirects=False,
        )
        response = await client.post(
            f"/games/{game_id}/characters",
            data={"name": "Second", "description": "", "notes": ""},
            follow_redirects=False,
        )
        assert response.status_code == 400
        chars = await _get_characters(game_id)
        assert len(chars) == 1

    async def test_empty_name_rejected(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        response = await client.post(
            f"/games/{game_id}/characters",
            data={"name": "   ", "description": "", "notes": ""},
            follow_redirects=False,
        )
        assert response.status_code == 422
        chars = await _get_characters(game_id)
        assert len(chars) == 0

    async def test_nonmember_blocked(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/characters",
            data={"name": "Intruder", "description": "", "notes": ""},
            follow_redirects=False,
        )
        assert response.status_code == 403
        chars = await _get_characters(game_id)
        assert len(chars) == 0

    async def test_blocked_during_setup(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        response = await client.post(
            f"/games/{game_id}/characters",
            data={"name": "Early", "description": "", "notes": ""},
            follow_redirects=False,
        )
        assert response.status_code == 403
        chars = await _get_characters(game_id)
        assert len(chars) == 0

    async def test_multiple_players_can_each_create_one(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await client.post(
            f"/games/{game_id}/characters",
            data={"name": "Alice Char", "description": "", "notes": ""},
            follow_redirects=False,
        )
        await _add_member(game_id, 2)
        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/characters",
            data={"name": "Bob Char", "description": "", "notes": ""},
            follow_redirects=False,
        )
        chars = await _get_characters(game_id)
        assert len(chars) == 2


class TestEditCharacter:
    async def _setup_with_char(self, client: AsyncClient) -> tuple[int, int]:
        """Create game as Alice (active), create character, return (game_id, char_id)."""
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(game_id)
        await client.post(
            f"/games/{game_id}/characters",
            data={"name": "Aria", "description": "Original desc", "notes": "Original notes"},
            follow_redirects=False,
        )
        chars = await _get_characters(game_id)
        return game_id, chars[0].id

    async def test_edit_page_loads_for_owner(self, client: AsyncClient) -> None:
        game_id, char_id = await self._setup_with_char(client)
        response = await client.get(f"/games/{game_id}/characters/{char_id}/edit")
        assert response.status_code == 200
        assert "Aria" in response.text
        assert "Original desc" in response.text

    async def test_owner_can_update(self, client: AsyncClient) -> None:
        game_id, char_id = await self._setup_with_char(client)
        response = await client.post(
            f"/games/{game_id}/characters/{char_id}/edit",
            data={"name": "Aria Revised", "description": "New desc", "notes": "New notes"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        chars = await _get_characters(game_id)
        assert chars[0].name == "Aria Revised"
        assert chars[0].description == "New desc"
        assert chars[0].notes == "New notes"

    async def test_organizer_cannot_edit_others(self, client: AsyncClient) -> None:
        # Organizer has no narrative privilege — they cannot edit another player's character
        game_id, char_id = await self._setup_with_char(client)
        await _add_member(game_id, 2)
        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/characters",
            data={"name": "Bob Char", "description": "", "notes": ""},
            follow_redirects=False,
        )
        # Alice (organizer) attempts to edit Bob's character
        await _login(client, 1)
        bob_chars = [c for c in await _get_characters(game_id) if c.name == "Bob Char"]
        bob_char_id = bob_chars[0].id
        response = await client.post(
            f"/games/{game_id}/characters/{bob_char_id}/edit",
            data={"name": "Bob Char Updated", "description": "", "notes": ""},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_player_cannot_edit_others(self, client: AsyncClient) -> None:
        game_id, char_id = await self._setup_with_char(client)
        await _add_member(game_id, 2)
        await _login(client, 2)
        # Bob tries to edit Alice's character
        response = await client.post(
            f"/games/{game_id}/characters/{char_id}/edit",
            data={"name": "Hijacked", "description": "", "notes": ""},
            follow_redirects=False,
        )
        assert response.status_code == 403
        chars = await _get_characters(game_id)
        assert chars[0].name == "Aria"

    async def test_empty_name_rejected_on_edit(self, client: AsyncClient) -> None:
        game_id, char_id = await self._setup_with_char(client)
        response = await client.post(
            f"/games/{game_id}/characters/{char_id}/edit",
            data={"name": "  ", "description": "", "notes": ""},
            follow_redirects=False,
        )
        assert response.status_code == 422
        chars = await _get_characters(game_id)
        assert chars[0].name == "Aria"

    async def test_nonmember_cannot_see_edit_page(self, client: AsyncClient) -> None:
        game_id, char_id = await self._setup_with_char(client)
        await _login(client, 2)
        response = await client.get(f"/games/{game_id}/characters/{char_id}/edit")
        assert response.status_code == 403

    async def test_char_not_found_returns_404(self, client: AsyncClient) -> None:
        game_id, _ = await self._setup_with_char(client)
        response = await client.get(f"/games/{game_id}/characters/99999/edit")
        assert response.status_code == 404
