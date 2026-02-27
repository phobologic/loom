"""Tests for NPC creation and management routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loom.models import NPC, Game, GameMember, GameStatus, MemberRole


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
