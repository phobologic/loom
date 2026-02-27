"""Tests for Session 0 wizard routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loom.models import (
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    PromptStatus,
    Session0Prompt,
    Session0Response,
    User,
)


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
    return int(location.rsplit("/", 1)[-1])


async def _add_member(
    db: AsyncSession, game_id: int, user_id: int, role: MemberRole = MemberRole.player
) -> None:
    """Directly insert a game member into the DB."""
    db.add(GameMember(game_id=game_id, user_id=user_id, role=role))
    await db.commit()


async def _get_prompts(db: AsyncSession, game_id: int) -> list[Session0Prompt]:
    """Fetch all session0 prompts for a game, ordered."""
    db.expire_all()
    result = await db.execute(
        select(Session0Prompt)
        .where(Session0Prompt.game_id == game_id)
        .order_by(Session0Prompt.order)
    )
    return list(result.scalars().all())


async def _get_prompt(db: AsyncSession, prompt_id: int) -> Session0Prompt | None:
    """Fetch a single session0 prompt by ID."""
    db.expire_all()
    result = await db.execute(select(Session0Prompt).where(Session0Prompt.id == prompt_id))
    return result.scalar_one_or_none()


async def _get_responses(db: AsyncSession, prompt_id: int) -> list[Session0Response]:
    """Fetch all responses for a prompt."""
    db.expire_all()
    result = await db.execute(
        select(Session0Response).where(Session0Response.prompt_id == prompt_id)
    )
    return list(result.scalars().all())


class TestSession0WizardInit:
    async def test_wizard_redirects_to_first_prompt(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        response = await client.get(f"/games/{game_id}/session0", follow_redirects=False)
        assert response.status_code == 303
        assert f"/games/{game_id}/session0/" in response.headers["location"]

    async def test_wizard_seeds_default_prompts(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await client.get(f"/games/{game_id}/session0", follow_redirects=False)
        prompts = await _get_prompts(db, game_id)
        assert len(prompts) == 7
        assert prompts[0].status == PromptStatus.active
        assert all(p.status == PromptStatus.pending for p in prompts[1:])
        assert prompts[5].is_word_seeds is True
        assert prompts[6].is_safety_tools is True
        assert all(not p.is_safety_tools for p in prompts[:6])
        assert all(not p.is_word_seeds for p in prompts[:5])

    async def test_wizard_requires_membership(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _login(client, 2)  # Bob is not a member
        response = await client.get(f"/games/{game_id}/session0", follow_redirects=False)
        assert response.status_code == 403

    async def test_wizard_requires_auth(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        # Log out by clearing session
        await client.post("/dev/logout", follow_redirects=False)
        response = await client.get(f"/games/{game_id}/session0", follow_redirects=False)
        assert response.status_code == 302


class TestSession0PromptView:
    async def _setup(self, client: AsyncClient) -> tuple[int, int]:
        """Create game, seed prompts, return (game_id, first_prompt_id)."""
        await _login(client, 1)
        game_id = await _create_game(client, pitch="A noir mystery game")
        r = await client.get(f"/games/{game_id}/session0", follow_redirects=False)
        prompt_id = int(r.headers["location"].rsplit("/", 1)[-1])
        return game_id, prompt_id

    async def test_shows_question_text(self, client: AsyncClient) -> None:
        game_id, prompt_id = await self._setup(client)
        response = await client.get(f"/games/{game_id}/session0/{prompt_id}")
        assert response.status_code == 200
        assert "genre" in response.text.lower() or "aesthetic" in response.text.lower()

    async def test_shows_pitch_context(self, client: AsyncClient) -> None:
        game_id, prompt_id = await self._setup(client)
        response = await client.get(f"/games/{game_id}/session0/{prompt_id}")
        assert "noir mystery game" in response.text

    async def test_shows_all_prompts_in_sidebar(self, client: AsyncClient) -> None:
        game_id, prompt_id = await self._setup(client)
        response = await client.get(f"/games/{game_id}/session0/{prompt_id}")
        assert response.text.count("/session0/") >= 5

    async def test_shows_response_form_when_active(self, client: AsyncClient) -> None:
        game_id, prompt_id = await self._setup(client)
        response = await client.get(f"/games/{game_id}/session0/{prompt_id}")
        assert 'name="content"' in response.text

    async def test_no_response_form_when_skipped(self, client: AsyncClient) -> None:
        game_id, prompt_id = await self._setup(client)
        await client.post(f"/games/{game_id}/session0/{prompt_id}/skip", follow_redirects=False)
        response = await client.get(f"/games/{game_id}/session0/{prompt_id}")
        assert 'name="content"' not in response.text


class TestSession0Respond:
    async def _setup(self, client: AsyncClient) -> tuple[int, int]:
        await _login(client, 1)
        game_id = await _create_game(client)
        r = await client.get(f"/games/{game_id}/session0", follow_redirects=False)
        prompt_id = int(r.headers["location"].rsplit("/", 1)[-1])
        return game_id, prompt_id

    async def test_player_can_submit_response(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, prompt_id = await self._setup(client)
        response = await client.post(
            f"/games/{game_id}/session0/{prompt_id}/respond",
            data={"content": "Dark noir with gothic elements"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        responses = await _get_responses(db, prompt_id)
        assert len(responses) == 1
        assert responses[0].content == "Dark noir with gothic elements"

    async def test_player_can_update_response(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, prompt_id = await self._setup(client)
        await client.post(
            f"/games/{game_id}/session0/{prompt_id}/respond",
            data={"content": "First response"},
            follow_redirects=False,
        )
        await client.post(
            f"/games/{game_id}/session0/{prompt_id}/respond",
            data={"content": "Updated response"},
            follow_redirects=False,
        )
        responses = await _get_responses(db, prompt_id)
        assert len(responses) == 1
        assert responses[0].content == "Updated response"

    async def test_response_visible_to_other_players(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, prompt_id = await self._setup(client)
        await _add_member(db, game_id, 2)

        # Alice submits
        await client.post(
            f"/games/{game_id}/session0/{prompt_id}/respond",
            data={"content": "Alice contribution to the genre"},
            follow_redirects=False,
        )

        # Bob views the prompt
        await _login(client, 2)
        response = await client.get(f"/games/{game_id}/session0/{prompt_id}")
        assert "Alice contribution to the genre" in response.text

    async def test_cannot_respond_to_non_active_prompt(self, client: AsyncClient) -> None:
        game_id, prompt_id = await self._setup(client)
        # Skip the prompt (moves it to skipped status)
        await client.post(f"/games/{game_id}/session0/{prompt_id}/skip", follow_redirects=False)
        response = await client.post(
            f"/games/{game_id}/session0/{prompt_id}/respond",
            data={"content": "Too late"},
            follow_redirects=False,
        )
        assert response.status_code == 403


class TestSession0OrganizerControls:
    async def _setup(self, client: AsyncClient) -> tuple[int, int]:
        await _login(client, 1)
        game_id = await _create_game(client)
        r = await client.get(f"/games/{game_id}/session0", follow_redirects=False)
        prompt_id = int(r.headers["location"].rsplit("/", 1)[-1])
        return game_id, prompt_id

    async def test_skip_advances_wizard(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, prompt_id = await self._setup(client)
        response = await client.post(
            f"/games/{game_id}/session0/{prompt_id}/skip", follow_redirects=False
        )
        assert response.status_code == 303
        prompt = await _get_prompt(db, prompt_id)
        assert prompt.status == PromptStatus.skipped
        prompts = await _get_prompts(db, game_id)
        active = [p for p in prompts if p.status == PromptStatus.active]
        assert len(active) == 1

    async def test_player_cannot_skip(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, prompt_id = await self._setup(client)
        await _add_member(db, game_id, 2)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/session0/{prompt_id}/skip", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_synthesize_stores_synthesis(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, prompt_id = await self._setup(client)
        await client.post(
            f"/games/{game_id}/session0/{prompt_id}/respond",
            data={"content": "Dark fantasy with steampunk aesthetics"},
            follow_redirects=False,
        )
        response = await client.post(
            f"/games/{game_id}/session0/{prompt_id}/synthesize", follow_redirects=False
        )
        assert response.status_code == 303
        prompt = await _get_prompt(db, prompt_id)
        assert prompt.synthesis is not None
        assert len(prompt.synthesis) > 0
        assert prompt.synthesis_accepted is False

    async def test_player_cannot_synthesize(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, prompt_id = await self._setup(client)
        await _add_member(db, game_id, 2)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/session0/{prompt_id}/synthesize", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_accept_marks_prompt_complete(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, prompt_id = await self._setup(client)
        await client.post(
            f"/games/{game_id}/session0/{prompt_id}/synthesize", follow_redirects=False
        )
        response = await client.post(
            f"/games/{game_id}/session0/{prompt_id}/accept", follow_redirects=False
        )
        assert response.status_code == 303
        prompt = await _get_prompt(db, prompt_id)
        assert prompt.status == PromptStatus.complete
        assert prompt.synthesis_accepted is True
        # Next prompt should be active
        prompts = await _get_prompts(db, game_id)
        active = [p for p in prompts if p.status == PromptStatus.active]
        assert len(active) == 1
        assert active[0].id != prompt_id

    async def test_regenerate_overwrites_synthesis(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, prompt_id = await self._setup(client)
        await client.post(
            f"/games/{game_id}/session0/{prompt_id}/synthesize", follow_redirects=False
        )
        first = (await _get_prompt(db, prompt_id)).synthesis
        response = await client.post(
            f"/games/{game_id}/session0/{prompt_id}/regenerate", follow_redirects=False
        )
        assert response.status_code == 303
        prompt = await _get_prompt(db, prompt_id)
        # Stub returns same text, but synthesis should still be set and accepted=False
        assert prompt.synthesis == first
        assert prompt.synthesis_accepted is False

    async def test_add_custom_prompt(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, _ = await self._setup(client)
        response = await client.post(
            f"/games/{game_id}/session0/prompts/add",
            data={"question": "What secret societies exist?"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        prompts = await _get_prompts(db, game_id)
        assert len(prompts) == 8
        custom = prompts[-1]
        assert custom.is_default is False
        assert custom.question == "What secret societies exist?"

    async def test_move_prompt_up(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, _ = await self._setup(client)
        prompts = await _get_prompts(db, game_id)
        # prompts[2] and prompts[1] are both pending — swap them
        target_id = prompts[2].id
        neighbor_id = prompts[1].id
        original_order = prompts[2].order
        neighbor_order = prompts[1].order
        response = await client.post(
            f"/games/{game_id}/session0/prompts/{target_id}/move",
            data={"direction": "up"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        updated = await _get_prompt(db, target_id)
        assert updated.order == neighbor_order
        updated_neighbor = await _get_prompt(db, neighbor_id)
        assert updated_neighbor.order == original_order

    async def test_cannot_move_pending_prompt_past_active(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, _ = await self._setup(client)
        prompts = await _get_prompts(db, game_id)
        # prompts[0] is active; moving prompts[1] up should be rejected
        target = prompts[1]
        response = await client.post(
            f"/games/{game_id}/session0/prompts/{target.id}/move",
            data={"direction": "up"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_cannot_move_complete_prompt(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, prompt_id = await self._setup(client)
        # Complete the first prompt
        await client.post(
            f"/games/{game_id}/session0/{prompt_id}/synthesize", follow_redirects=False
        )
        await client.post(f"/games/{game_id}/session0/{prompt_id}/accept", follow_redirects=False)
        response = await client.post(
            f"/games/{game_id}/session0/prompts/{prompt_id}/move",
            data={"direction": "down"},
            follow_redirects=False,
        )
        assert response.status_code == 403


class TestSession0Completion:
    async def _setup(self, client: AsyncClient) -> int:
        await _login(client, 1)
        return await _create_game(client)

    async def _skip_all(self, client: AsyncClient, db: AsyncSession, game_id: int) -> None:
        """Seed and skip all prompts."""
        await client.get(f"/games/{game_id}/session0", follow_redirects=False)
        while True:
            prompts = await _get_prompts(db, game_id)
            active = next((p for p in prompts if p.status == PromptStatus.active), None)
            if active is None:
                break
            r = await client.post(
                f"/games/{game_id}/session0/{active.id}/skip", follow_redirects=False
            )
            assert r.status_code == 303

    async def test_complete_session0_advances_game_status(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await self._setup(client)
        await self._skip_all(client, db, game_id)
        response = await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == f"/games/{game_id}"
        db.expire_all()
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one()
        assert game.status == GameStatus.active

    async def test_cannot_complete_with_pending_prompts(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        # Seed but don't complete all
        await client.get(f"/games/{game_id}/session0", follow_redirects=False)
        response = await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        assert response.status_code == 403
