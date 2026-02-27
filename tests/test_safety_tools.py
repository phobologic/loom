"""Tests for safety tools (lines and veils) routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loom.models import (
    GameMember,
    GameSafetyTool,
    MemberRole,
    PromptStatus,
    SafetyToolKind,
    Session0Prompt,
    User,
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


async def _get_safety_tools(db: AsyncSession, game_id: int) -> list[GameSafetyTool]:
    db.expire_all()
    result = await db.execute(
        select(GameSafetyTool)
        .where(GameSafetyTool.game_id == game_id)
        .order_by(GameSafetyTool.created_at)
    )
    return list(result.scalars().all())


async def _seed_session0(client: AsyncClient, game_id: int) -> None:
    """Trigger Session 0 seeding by visiting the wizard."""
    await client.get(f"/games/{game_id}/session0", follow_redirects=False)


async def _get_safety_tools_prompt_id(db: AsyncSession, game_id: int) -> int:
    db.expire_all()
    result = await db.execute(
        select(Session0Prompt).where(
            Session0Prompt.game_id == game_id,
            Session0Prompt.is_safety_tools.is_(True),
        )
    )
    prompt = result.scalar_one()
    return prompt.id


class TestSafetyToolsPage:
    async def _setup(self, client: AsyncClient) -> int:
        await _login(client, 1)
        return await _create_game(client)

    async def test_page_loads_for_member(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        response = await client.get(f"/games/{game_id}/safety-tools")
        assert response.status_code == 200
        assert "Lines" in response.text
        assert "Veils" in response.text

    async def test_page_requires_membership(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await _login(client, 2)  # Bob is not a member
        response = await client.get(f"/games/{game_id}/safety-tools")
        assert response.status_code == 403

    async def test_page_requires_auth(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        # Clear session by logging in as nobody (hit an unprotected page)
        await client.get("/")
        # Manually clear cookie
        client.cookies.clear()
        response = await client.get(f"/games/{game_id}/safety-tools", follow_redirects=False)
        assert response.status_code in (302, 303)

    async def test_shows_lines_and_veils(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client)
        await _add_member(db, game_id, 2)
        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/safety-tools/add",
            data={"kind": "line", "description": "No torture scenes"},
            follow_redirects=False,
        )
        await client.post(
            f"/games/{game_id}/safety-tools/add",
            data={"kind": "veil", "description": "Sexual content"},
            follow_redirects=False,
        )
        response = await client.get(f"/games/{game_id}/safety-tools")
        assert "No torture scenes" in response.text
        assert "Sexual content" in response.text


class TestAddSafetyTool:
    async def _setup(self, client: AsyncClient) -> int:
        await _login(client, 1)
        return await _create_game(client)

    async def test_organizer_can_add_line(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client)
        response = await client.post(
            f"/games/{game_id}/safety-tools/add",
            data={"kind": "line", "description": "No gratuitous violence"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        tools = await _get_safety_tools(db, game_id)
        assert len(tools) == 1
        assert tools[0].kind == SafetyToolKind.line
        assert tools[0].description == "No gratuitous violence"

    async def test_player_can_add_veil(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client)
        await _add_member(db, game_id, 2)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/safety-tools/add",
            data={"kind": "veil", "description": "Child endangerment"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        tools = await _get_safety_tools(db, game_id)
        assert len(tools) == 1
        assert tools[0].kind == SafetyToolKind.veil
        assert tools[0].description == "Child endangerment"

    async def test_multiple_members_can_add(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client)
        await _add_member(db, game_id, 2)
        await client.post(
            f"/games/{game_id}/safety-tools/add",
            data={"kind": "line", "description": "Alice's line"},
            follow_redirects=False,
        )
        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/safety-tools/add",
            data={"kind": "veil", "description": "Bob's veil"},
            follow_redirects=False,
        )
        tools = await _get_safety_tools(db, game_id)
        assert len(tools) == 2

    async def test_invalid_kind_rejected(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client)
        response = await client.post(
            f"/games/{game_id}/safety-tools/add",
            data={"kind": "invalid", "description": "Something"},
            follow_redirects=False,
        )
        assert response.status_code == 422
        tools = await _get_safety_tools(db, game_id)
        assert len(tools) == 0

    async def test_empty_description_rejected(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client)
        response = await client.post(
            f"/games/{game_id}/safety-tools/add",
            data={"kind": "line", "description": "   "},
            follow_redirects=False,
        )
        assert response.status_code == 422
        tools = await _get_safety_tools(db, game_id)
        assert len(tools) == 0

    async def test_nonmember_cannot_add(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client)
        await _login(client, 2)  # Bob is not a member
        response = await client.post(
            f"/games/{game_id}/safety-tools/add",
            data={"kind": "line", "description": "Something"},
            follow_redirects=False,
        )
        assert response.status_code == 403
        tools = await _get_safety_tools(db, game_id)
        assert len(tools) == 0


class TestDeleteSafetyTool:
    async def _setup_with_tool(
        self,
        client: AsyncClient,
        db: AsyncSession,
        kind: str = "line",
        description: str = "No violence",
    ) -> tuple[int, int]:
        """Create game as Alice, add tool, return (game_id, tool_id)."""
        await _login(client, 1)
        game_id = await _create_game(client)
        await client.post(
            f"/games/{game_id}/safety-tools/add",
            data={"kind": kind, "description": description},
            follow_redirects=False,
        )
        tools = await _get_safety_tools(db, game_id)
        return game_id, tools[0].id

    async def test_owner_can_delete_own(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, tool_id = await self._setup_with_tool(client, db)
        response = await client.post(
            f"/games/{game_id}/safety-tools/{tool_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        tools = await _get_safety_tools(db, game_id)
        assert len(tools) == 0

    async def test_organizer_can_delete_any(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, _ = await self._setup_with_tool(client, db)
        await _add_member(db, game_id, 2)
        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/safety-tools/add",
            data={"kind": "veil", "description": "Bob's veil"},
            follow_redirects=False,
        )
        tools = await _get_safety_tools(db, game_id)
        bob_tool_id = next(t.id for t in tools if t.description == "Bob's veil")

        # Alice (organizer) deletes Bob's tool
        await _login(client, 1)
        response = await client.post(
            f"/games/{game_id}/safety-tools/{bob_tool_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303
        tools = await _get_safety_tools(db, game_id)
        assert all(t.description != "Bob's veil" for t in tools)

    async def test_player_cannot_delete_others(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, tool_id = await self._setup_with_tool(client, db)
        await _add_member(db, game_id, 2)
        await _login(client, 2)  # Bob is a player
        response = await client.post(
            f"/games/{game_id}/safety-tools/{tool_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 403
        tools = await _get_safety_tools(db, game_id)
        assert len(tools) == 1

    async def test_nonmember_cannot_delete(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, tool_id = await self._setup_with_tool(client, db)
        await _login(client, 2)  # Bob is not a member
        response = await client.post(
            f"/games/{game_id}/safety-tools/{tool_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_tool_not_found_in_wrong_game(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await _login(client, 1)
        game_id1, tool_id = await self._setup_with_tool(client, db)
        game_id2 = await _create_game(client, name="Other Game")
        response = await client.post(
            f"/games/{game_id2}/safety-tools/{tool_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 404


class TestSafetyToolsInSession0Wizard:
    async def _setup(self, client: AsyncClient, db: AsyncSession) -> tuple[int, int]:
        """Create game, seed Session 0, return (game_id, safety_tools_prompt_id)."""
        await _login(client, 1)
        game_id = await _create_game(client)
        await _seed_session0(client, game_id)
        prompt_id = await _get_safety_tools_prompt_id(db, game_id)
        return game_id, prompt_id

    async def test_safety_tools_prompt_is_seeded(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, prompt_id = await self._setup(client, db)
        assert prompt_id is not None

    async def test_safety_tools_page_shows_structured_ui(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, prompt_id = await self._setup(client, db)
        # Advance wizard to the safety tools prompt by accepting previous ones
        db.expire_all()
        result = await db.execute(
            select(Session0Prompt)
            .where(Session0Prompt.game_id == game_id)
            .order_by(Session0Prompt.order)
        )
        prompts = list(result.scalars().all())
        # Mark all earlier prompts as complete
        for p in prompts:
            if p.id != prompt_id:
                p.status = PromptStatus.complete
            else:
                p.status = PromptStatus.active
        await db.commit()

        response = await client.get(f"/games/{game_id}/session0/{prompt_id}")
        assert response.status_code == 200
        assert "Lines" in response.text
        assert "Veils" in response.text
        assert "Add a line or veil" in response.text
        assert "Mark safety tools complete" in response.text

    async def test_mark_done_advances_wizard(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, prompt_id = await self._setup(client, db)
        # Make safety tools prompt active
        db.expire_all()
        result = await db.execute(select(Session0Prompt).where(Session0Prompt.id == prompt_id))
        prompt = result.scalar_one()
        prompt.status = PromptStatus.active
        await db.commit()

        response = await client.post(
            f"/games/{game_id}/session0/{prompt_id}/mark-done",
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        result = await db.execute(select(Session0Prompt).where(Session0Prompt.id == prompt_id))
        prompt = result.scalar_one()
        assert prompt.status == PromptStatus.complete

    async def test_player_cannot_mark_done(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, prompt_id = await self._setup(client, db)
        await _add_member(db, game_id, 2)
        db.expire_all()
        result = await db.execute(select(Session0Prompt).where(Session0Prompt.id == prompt_id))
        prompt = result.scalar_one()
        prompt.status = PromptStatus.active
        await db.commit()

        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/session0/{prompt_id}/mark-done",
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_mark_done_rejects_non_safety_tools_prompt(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, _ = await self._setup(client, db)
        # Get the first (non-safety-tools) prompt
        db.expire_all()
        result = await db.execute(
            select(Session0Prompt)
            .where(
                Session0Prompt.game_id == game_id,
                Session0Prompt.is_safety_tools.is_(False),
            )
            .order_by(Session0Prompt.order)
        )
        regular_prompt = result.scalars().first()
        regular_prompt_id = regular_prompt.id

        response = await client.post(
            f"/games/{game_id}/session0/{regular_prompt_id}/mark-done",
            follow_redirects=False,
        )
        assert response.status_code == 400

    async def test_tools_added_during_session0_visible_on_standalone_page(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, _ = await self._setup(client, db)
        await client.post(
            f"/games/{game_id}/safety-tools/add",
            data={"kind": "line", "description": "No horror content"},
            follow_redirects=False,
        )
        response = await client.get(f"/games/{game_id}/safety-tools")
        assert "No horror content" in response.text
