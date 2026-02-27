"""Tests for NPC creation and management routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loom.models import (
    NPC,
    Act,
    ActStatus,
    Beat,
    Event,
    EventType,
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    Notification,
    NotificationType,
    Scene,
    SceneStatus,
)


async def _login(client: AsyncClient, user_id: int) -> None:
    await client.post("/dev/login", data={"user_id": str(user_id)}, follow_redirects=False)


async def _create_game(client: AsyncClient, name: str = "Test Game") -> int:
    response = await client.post("/games", data={"name": name, "pitch": ""}, follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]
    return int(location.rsplit("/", 1)[-1])


async def _add_member(
    db: AsyncSession, game_id: int, user_id: int, role: MemberRole = MemberRole.player
) -> None:
    db.add(GameMember(game_id=game_id, user_id=user_id, role=role))
    await db.commit()


async def _activate_game(db: AsyncSession, game_id: int) -> None:
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one()
    game.status = GameStatus.active
    await db.commit()


async def _get_npcs(db: AsyncSession, game_id: int) -> list[NPC]:
    result = await db.execute(select(NPC).where(NPC.game_id == game_id).order_by(NPC.name))
    return list(result.scalars().all())


class TestNpcsPage:
    async def _setup(self, client: AsyncClient, db: AsyncSession) -> int:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        return game_id

    async def test_page_loads_for_member(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client, db)
        response = await client.get(f"/games/{game_id}/npcs")
        assert response.status_code == 200
        assert "NPCs" in response.text

    async def test_page_requires_membership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client, db)
        await _login(client, 2)
        response = await client.get(f"/games/{game_id}/npcs")
        assert response.status_code == 403

    async def test_page_blocked_during_setup(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        response = await client.get(f"/games/{game_id}/npcs")
        assert response.status_code == 403

    async def test_page_shows_add_form_for_active_game(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await self._setup(client, db)
        response = await client.get(f"/games/{game_id}/npcs")
        assert response.status_code == 200
        assert "Add NPC" in response.text


class TestCreateNpc:
    async def _setup(self, client: AsyncClient, db: AsyncSession) -> int:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        return game_id

    async def test_create_npc(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client, db)
        response = await client.post(
            f"/games/{game_id}/npcs",
            data={
                "name": "Thornwick",
                "description": "A weathered innkeeper",
                "notes": "Knows secrets",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == f"/games/{game_id}/npcs"

        npcs = await _get_npcs(db, game_id)
        assert len(npcs) == 1
        assert npcs[0].name == "Thornwick"
        assert npcs[0].description == "A weathered innkeeper"
        assert npcs[0].notes == "Knows secrets"
        assert npcs[0].game_id == game_id

    async def test_create_npc_requires_name(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client, db)
        response = await client.post(
            f"/games/{game_id}/npcs",
            data={"name": "   ", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_any_member_can_create_npc(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client, db)
        await _add_member(db, game_id, 2)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/npcs",
            data={"name": "Mira", "description": "", "notes": ""},
            follow_redirects=False,
        )
        assert response.status_code == 303
        npcs = await _get_npcs(db, game_id)
        assert any(n.name == "Mira" for n in npcs)

    async def test_non_member_cannot_create_npc(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await self._setup(client, db)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/npcs",
            data={"name": "Intruder", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 403


class TestEditNpc:
    async def _setup_with_npc(self, client: AsyncClient, db: AsyncSession) -> tuple[int, int]:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        db.add(NPC(game_id=game_id, name="OldName", description="Old desc", notes="Old notes"))
        await db.commit()
        npcs = await _get_npcs(db, game_id)
        return game_id, npcs[0].id

    async def test_edit_page_loads(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, npc_id = await self._setup_with_npc(client, db)
        response = await client.get(f"/games/{game_id}/npcs/{npc_id}/edit")
        assert response.status_code == 200
        assert "OldName" in response.text

    async def test_update_npc(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, npc_id = await self._setup_with_npc(client, db)
        response = await client.post(
            f"/games/{game_id}/npcs/{npc_id}/edit",
            data={"name": "NewName", "description": "New desc", "notes": "New notes"},
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        result = await db.execute(select(NPC).where(NPC.id == npc_id))
        npc = result.scalar_one()
        assert npc.name == "NewName"
        assert npc.description == "New desc"
        assert npc.notes == "New notes"

    async def test_any_member_can_edit_npc(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, npc_id = await self._setup_with_npc(client, db)
        await _add_member(db, game_id, 2)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/npcs/{npc_id}/edit",
            data={"name": "EditedByBob", "description": "", "notes": ""},
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        result = await db.execute(select(NPC).where(NPC.id == npc_id))
        npc = result.scalar_one()
        assert npc.name == "EditedByBob"

    async def test_non_member_cannot_edit_npc(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, npc_id = await self._setup_with_npc(client, db)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/npcs/{npc_id}/edit",
            data={"name": "Hack", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Beat-triggered NPC creation
# ---------------------------------------------------------------------------


async def _create_beat_with_text(
    db: AsyncSession, game_id: int, text: str = "A mysterious figure appeared."
) -> int:
    """Create an act, scene, and beat with a narrative event; return beat_id."""
    act = Act(
        game_id=game_id,
        guiding_question="What lurks here?",
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
        tension=5,
    )
    db.add(scene)
    await db.flush()
    beat = Beat(scene_id=scene.id, author_id=1)
    db.add(beat)
    await db.flush()
    event = Event(beat_id=beat.id, type=EventType.narrative, content=text, order=0)
    db.add(event)
    await db.commit()
    return beat.id


class TestNpcFromBeat:
    async def _setup(self, client: AsyncClient, db: AsyncSession) -> tuple[int, int]:
        """Create active game as Alice and a beat with narrative text. Return (game_id, beat_id)."""
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        beat_id = await _create_beat_with_text(db, game_id)
        return game_id, beat_id

    async def test_form_page_loads(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, beat_id = await self._setup(client, db)
        response = await client.get(f"/games/{game_id}/beats/{beat_id}/npc/new")
        assert response.status_code == 200
        assert "Who is this person" in response.text
        assert "Get AI ideas" in response.text

    async def test_form_shows_beat_text(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, beat_id = await self._setup(client, db)
        response = await client.get(f"/games/{game_id}/beats/{beat_id}/npc/new")
        assert response.status_code == 200
        assert "A mysterious figure appeared" in response.text

    async def test_form_blocked_for_non_member(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, beat_id = await self._setup(client, db)
        await _login(client, 2)
        response = await client.get(f"/games/{game_id}/beats/{beat_id}/npc/new")
        assert response.status_code == 403

    async def test_form_blocked_during_setup(self, client: AsyncClient, db: AsyncSession) -> None:
        """Beat-to-NPC form is blocked when game is in setup (not yet active)."""
        await _login(client, 1)
        game_id = await _create_game(client)
        # Game is in setup status; create a scene and beat anyway to test auth
        beat_id = await _create_beat_with_text(db, game_id)
        response = await client.get(f"/games/{game_id}/beats/{beat_id}/npc/new")
        assert response.status_code == 403

    async def test_suggest_returns_fragment(
        self, client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST to suggest returns HTML fragment (even with empty AI suggestions)."""
        game_id, beat_id = await self._setup(client, db)
        response = await client.post(
            f"/games/{game_id}/beats/{beat_id}/npc/suggest",
            data={"description": "An imperial spy", "name": "", "notes": ""},
        )
        assert response.status_code == 200
        # Should return the suggestions partial (may be empty suggestions message)
        assert "suggestions" in response.text.lower() or "No suggestions" in response.text

    async def test_suggest_returns_ai_options(
        self, client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST to suggest populates suggestions when AI returns results."""

        async def _mock_suggest(beat_text, role, *, name=None, want=None, **kwargs):
            return (["Cassius Thorn", "Elara Kent"], ["To uncover the rebel cell"])

        monkeypatch.setattr("loom.routers.npcs.suggest_npc_details", _mock_suggest)

        game_id, beat_id = await self._setup(client, db)
        response = await client.post(
            f"/games/{game_id}/beats/{beat_id}/npc/suggest",
            data={"description": "An imperial spy", "name": "", "notes": ""},
        )
        assert response.status_code == 200
        assert "Cassius Thorn" in response.text
        assert "Elara Kent" in response.text
        assert "To uncover the rebel cell" in response.text

    async def test_suggest_graceful_on_ai_failure(
        self, client: AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If AI raises, suggest endpoint returns empty fragment (not 500)."""

        async def _failing_suggest(*args, **kwargs):
            raise RuntimeError("AI unavailable")

        monkeypatch.setattr("loom.routers.npcs.suggest_npc_details", _failing_suggest)

        game_id, beat_id = await self._setup(client, db)
        response = await client.post(
            f"/games/{game_id}/beats/{beat_id}/npc/suggest",
            data={"description": "A guard captain", "name": "", "notes": ""},
        )
        assert response.status_code == 200

    async def test_suggest_blocked_for_non_member(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, beat_id = await self._setup(client, db)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/beats/{beat_id}/npc/suggest",
            data={"description": "A spy", "name": "", "notes": ""},
        )
        assert response.status_code == 403

    async def test_create_npc_sends_notification(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        """Creating an NPC via the standard endpoint notifies other members."""
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        await _add_member(db, game_id, 2)

        response = await client.post(
            f"/games/{game_id}/npcs",
            data={"name": "Lord Blackwood", "description": "A noble", "notes": ""},
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        result = await db.execute(
            select(Notification)
            .where(Notification.game_id == game_id)
            .where(Notification.notification_type == NotificationType.npc_created)
        )
        notifications = list(result.scalars().all())
        # Should notify Bob (user 2) but not Alice (creator)
        assert len(notifications) == 1
        assert notifications[0].user_id == 2
        assert "Lord Blackwood" in notifications[0].message

    async def test_create_npc_no_notification_to_creator(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        """The NPC creator does not receive their own notification."""
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)

        await client.post(
            f"/games/{game_id}/npcs",
            data={"name": "Solo NPC", "description": "Made alone", "notes": ""},
            follow_redirects=False,
        )

        db.expire_all()
        result = await db.execute(
            select(Notification)
            .where(Notification.game_id == game_id)
            .where(Notification.notification_type == NotificationType.npc_created)
            .where(Notification.user_id == 1)
        )
        notifications = list(result.scalars().all())
        assert len(notifications) == 0

    async def test_beat_link_visible_on_scene(self, client: AsyncClient, db: AsyncSession) -> None:
        """Scene view shows 'Add NPC from this beat' link for active games."""
        game_id, beat_id = await self._setup(client, db)
        # Get the scene URL from the beat's scene
        db.expire_all()
        beat_result = await db.execute(select(Beat).where(Beat.id == beat_id))
        beat = beat_result.scalar_one()
        scene_id = beat.scene_id
        act_result = await db.execute(select(Scene).where(Scene.id == scene_id))
        scene = act_result.scalar_one()
        act_id = scene.act_id

        response = await client.get(f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}")
        assert response.status_code == 200
        assert "Add NPC from this beat" in response.text
