"""Tests for world document generation and voting routes."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from loom.database import Base, get_db
from loom.main import _DEV_USERS, app
from loom.models import (
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    PromptStatus,
    ProposalStatus,
    ProposalType,
    Session0Prompt,
    User,
    Vote,
    VoteChoice,
    VoteProposal,
    WorldDocument,
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


async def _create_game(client: AsyncClient, name: str = "Test Game", pitch: str = "A pitch") -> int:
    response = await client.post(
        "/games", data={"name": name, "pitch": pitch}, follow_redirects=False
    )
    assert response.status_code == 303
    return int(response.headers["location"].rsplit("/", 1)[-1])


async def _add_member(game_id: int, user_id: int, role: MemberRole = MemberRole.player) -> None:
    async with _test_session_factory() as db:
        db.add(GameMember(game_id=game_id, user_id=user_id, role=role))
        await db.commit()


async def _skip_all_prompts(client: AsyncClient, game_id: int) -> None:
    """Seed and skip all Session 0 prompts."""
    await client.get(f"/games/{game_id}/session0", follow_redirects=False)
    while True:
        async with _test_session_factory() as db:
            result = await db.execute(
                select(Session0Prompt)
                .where(Session0Prompt.game_id == game_id)
                .order_by(Session0Prompt.order)
            )
            prompts = list(result.scalars().all())
        active = next((p for p in prompts if p.status == PromptStatus.active), None)
        if active is None:
            break
        r = await client.post(f"/games/{game_id}/session0/{active.id}/skip", follow_redirects=False)
        assert r.status_code == 303


async def _get_game(game_id: int) -> Game:
    async with _test_session_factory() as db:
        result = await db.execute(select(Game).where(Game.id == game_id))
        return result.scalar_one()


async def _get_world_doc(game_id: int) -> WorldDocument | None:
    async with _test_session_factory() as db:
        result = await db.execute(select(WorldDocument).where(WorldDocument.game_id == game_id))
        return result.scalar_one_or_none()


async def _get_proposals(game_id: int) -> list[VoteProposal]:
    async with _test_session_factory() as db:
        result = await db.execute(select(VoteProposal).where(VoteProposal.game_id == game_id))
        return list(result.scalars().all())


async def _get_votes(proposal_id: int) -> list[Vote]:
    async with _test_session_factory() as db:
        result = await db.execute(select(Vote).where(Vote.proposal_id == proposal_id))
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# complete_session0 with auto-approval (single player)
# ---------------------------------------------------------------------------


class TestCompleteSession0SinglePlayer:
    async def _setup(self, client: AsyncClient) -> int:
        """Create game (only organizer), skip all prompts, return game_id."""
        await _login(client, 1)
        game_id = await _create_game(client)
        await _skip_all_prompts(client, game_id)
        return game_id

    async def test_generates_world_document(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        world_doc = await _get_world_doc(game_id)
        assert world_doc is not None
        assert len(world_doc.content) > 0

    async def test_creates_approved_proposal(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        proposals = await _get_proposals(game_id)
        assert len(proposals) == 1
        assert proposals[0].status == ProposalStatus.approved
        assert proposals[0].proposal_type == ProposalType.world_doc_approval

    async def test_records_implicit_yes_vote(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        proposals = await _get_proposals(game_id)
        votes = await _get_votes(proposals[0].id)
        assert len(votes) == 1
        assert votes[0].choice == VoteChoice.yes
        assert votes[0].voter_id == 1  # user Alice (id=1)

    async def test_game_status_becomes_active(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        game = await _get_game(game_id)
        assert game.status == GameStatus.active

    async def test_redirects_to_game_dashboard(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        response = await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == f"/games/{game_id}"

    async def test_cannot_complete_with_pending_prompts(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        # Seed but don't complete prompts
        await client.get(f"/games/{game_id}/session0", follow_redirects=False)
        response = await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# complete_session0 with multi-player (vote needed)
# ---------------------------------------------------------------------------


class TestCompleteSession0MultiPlayer:
    async def _setup(self, client: AsyncClient) -> int:
        """Create game with 2 members, skip all prompts."""
        await _login(client, 1)
        game_id = await _create_game(client)
        await _add_member(game_id, 2)  # Bob joins
        await _skip_all_prompts(client, game_id)
        return game_id

    async def test_redirects_to_world_document(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        response = await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == f"/games/{game_id}/world-document"

    async def test_proposal_remains_open(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        proposals = await _get_proposals(game_id)
        assert proposals[0].status == ProposalStatus.open

    async def test_game_remains_in_setup(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        game = await _get_game(game_id)
        assert game.status == GameStatus.setup

    async def test_second_vote_approves_game(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        proposals = await _get_proposals(game_id)
        proposal_id = proposals[0].id

        # Bob votes yes — should tip the threshold (2 of 2 players)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )
        assert response.status_code == 303

        game = await _get_game(game_id)
        assert game.status == GameStatus.active

    async def test_no_vote_does_not_approve(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        proposals = await _get_proposals(game_id)
        proposal_id = proposals[0].id

        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "no"},
            follow_redirects=False,
        )
        game = await _get_game(game_id)
        assert game.status == GameStatus.setup

    async def test_suggest_modification_stores_suggestion(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        proposals = await _get_proposals(game_id)
        proposal_id = proposals[0].id

        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "suggest_modification", "suggestion": "Make it darker"},
            follow_redirects=False,
        )
        votes = await _get_votes(proposal_id)
        suggest_vote = next(v for v in votes if v.choice == VoteChoice.suggest_modification)
        assert suggest_vote.suggestion == "Make it darker"

    async def test_cannot_vote_twice(self, client: AsyncClient) -> None:
        """A player cannot cast a second vote on an open proposal."""
        # Need 3 players so the proposal stays open after Bob's first vote
        await _login(client, 1)
        game_id = await _create_game(client)
        await _add_member(game_id, 2)
        await _add_member(game_id, 3)
        await _skip_all_prompts(client, game_id)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        proposals = await _get_proposals(game_id)
        proposal_id = proposals[0].id

        # Bob votes no (proposal still open — need 2 of 3 yes, only Alice voted yes so far)
        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "no"},
            follow_redirects=False,
        )
        # Bob tries to vote again on the still-open proposal
        response = await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )
        assert response.status_code == 409

    async def test_non_member_cannot_vote(self, client: AsyncClient) -> None:
        game_id = await self._setup(client)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        proposals = await _get_proposals(game_id)
        proposal_id = proposals[0].id

        await _login(client, 3)  # Charlie is not a member
        response = await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_three_player_threshold(self, client: AsyncClient) -> None:
        """In a 3-player game, 2 yes votes should approve (2 > 1.5)."""
        await _login(client, 1)
        game_id = await _create_game(client)
        await _add_member(game_id, 2)
        await _add_member(game_id, 3)
        await _skip_all_prompts(client, game_id)

        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        proposals = await _get_proposals(game_id)
        proposal_id = proposals[0].id

        # Alice already voted (implicit yes). Bob votes yes → 2 of 3 = approved.
        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )
        game = await _get_game(game_id)
        assert game.status == GameStatus.active

    async def test_idempotent_proposal_creation(self, client: AsyncClient) -> None:
        """Calling complete_session0 twice reuses the existing open proposal."""
        game_id = await self._setup(client)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)
        proposals = await _get_proposals(game_id)
        assert len(proposals) == 1  # only one proposal created


# ---------------------------------------------------------------------------
# World document view
# ---------------------------------------------------------------------------


class TestWorldDocumentView:
    async def test_view_requires_membership(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _login(client, 2)
        response = await client.get(f"/games/{game_id}/world-document", follow_redirects=False)
        assert response.status_code == 403

    async def test_view_shows_world_document(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _skip_all_prompts(client, game_id)
        await client.post(f"/games/{game_id}/session0/complete", follow_redirects=False)

        response = await client.get(f"/games/{game_id}/world-document", follow_redirects=False)
        assert response.status_code == 200
        assert b"World Document" in response.content

    async def test_view_without_world_doc(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        response = await client.get(f"/games/{game_id}/world-document", follow_redirects=False)
        assert response.status_code == 200
        assert b"No world document" in response.content


# ---------------------------------------------------------------------------
# Propose Ready to Play (early exit)
# ---------------------------------------------------------------------------


class TestProposeReadyToPlay:
    async def test_propose_ready_requires_pitch(self, client: AsyncClient) -> None:
        """Without any content, propose-ready should fail."""
        await _login(client, 1)
        game_id = await _create_game(client, pitch="")
        response = await client.post(
            f"/games/{game_id}/session0/propose-ready", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_propose_ready_with_pitch(self, client: AsyncClient) -> None:
        """A game with a pitch satisfies minimum requirements."""
        await _login(client, 1)
        game_id = await _create_game(client, pitch="A world of fog and ambition")
        response = await client.post(
            f"/games/{game_id}/session0/propose-ready", follow_redirects=False
        )
        assert response.status_code == 303

    async def test_single_player_auto_approves(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client, pitch="A world of fog")
        await client.post(f"/games/{game_id}/session0/propose-ready", follow_redirects=False)
        game = await _get_game(game_id)
        assert game.status == GameStatus.active

    async def test_multi_player_opens_vote(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client, pitch="A world of fog")
        await _add_member(game_id, 2)
        response = await client.post(
            f"/games/{game_id}/session0/propose-ready", follow_redirects=False
        )
        assert response.headers["location"] == f"/games/{game_id}/world-document"
        proposals = await _get_proposals(game_id)
        assert proposals[0].proposal_type == ProposalType.ready_to_play
        assert proposals[0].status == ProposalStatus.open

    async def test_non_member_cannot_propose(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client, pitch="A world of fog")
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/session0/propose-ready", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_cannot_propose_when_active(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client, pitch="A world of fog")
        # Auto-approve (1 player)
        await client.post(f"/games/{game_id}/session0/propose-ready", follow_redirects=False)
        response = await client.post(
            f"/games/{game_id}/session0/propose-ready", follow_redirects=False
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Game state transitions (pause / resume / archive)
# ---------------------------------------------------------------------------


class TestGameStateTransitions:
    async def _setup_active(self, client: AsyncClient) -> int:
        """Create a single-player game and activate it."""
        await _login(client, 1)
        game_id = await _create_game(client, pitch="A world")
        await client.post(f"/games/{game_id}/session0/propose-ready", follow_redirects=False)
        return game_id

    async def test_organizer_can_pause_active_game(self, client: AsyncClient) -> None:
        game_id = await self._setup_active(client)
        response = await client.post(f"/games/{game_id}/pause", follow_redirects=False)
        assert response.status_code == 303
        game = await _get_game(game_id)
        assert game.status == GameStatus.paused

    async def test_organizer_can_resume_paused_game(self, client: AsyncClient) -> None:
        game_id = await self._setup_active(client)
        await client.post(f"/games/{game_id}/pause", follow_redirects=False)
        response = await client.post(f"/games/{game_id}/resume", follow_redirects=False)
        assert response.status_code == 303
        game = await _get_game(game_id)
        assert game.status == GameStatus.active

    async def test_organizer_can_archive_game(self, client: AsyncClient) -> None:
        game_id = await self._setup_active(client)
        response = await client.post(f"/games/{game_id}/archive", follow_redirects=False)
        assert response.status_code == 303
        game = await _get_game(game_id)
        assert game.status == GameStatus.archived

    async def test_cannot_pause_setup_game(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        response = await client.post(f"/games/{game_id}/pause", follow_redirects=False)
        assert response.status_code == 403

    async def test_cannot_resume_active_game(self, client: AsyncClient) -> None:
        game_id = await self._setup_active(client)
        response = await client.post(f"/games/{game_id}/resume", follow_redirects=False)
        assert response.status_code == 403

    async def test_non_organizer_cannot_pause(self, client: AsyncClient) -> None:
        game_id = await self._setup_active(client)
        await _add_member(game_id, 2)
        await _login(client, 2)
        response = await client.post(f"/games/{game_id}/pause", follow_redirects=False)
        assert response.status_code == 403

    async def test_cannot_archive_already_archived(self, client: AsyncClient) -> None:
        game_id = await self._setup_active(client)
        await client.post(f"/games/{game_id}/archive", follow_redirects=False)
        await _login(client, 1)
        response = await client.post(f"/games/{game_id}/archive", follow_redirects=False)
        assert response.status_code == 403
