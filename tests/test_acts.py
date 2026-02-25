"""Tests for act creation and voting routes."""

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
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    ProposalStatus,
    ProposalType,
    Vote,
    VoteChoice,
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


async def _create_active_game(client: AsyncClient, extra_members: list[int] | None = None) -> int:
    """Create a game, add optional extra members, activate it via propose-ready."""
    await _login(client, 1)
    r = await client.post(
        "/games", data={"name": "Test Game", "pitch": "A pitch"}, follow_redirects=False
    )
    game_id = int(r.headers["location"].rsplit("/", 1)[-1])

    if extra_members:
        async with _test_session_factory() as db:
            for uid in extra_members:
                db.add(GameMember(game_id=game_id, user_id=uid, role=MemberRole.player))
            await db.commit()

    # activate via propose-ready (single player with only Alice auto-approves)
    # if extra members were added, we need to vote them in too — use direct DB manipulation
    if not extra_members:
        await client.post(f"/games/{game_id}/session0/propose-ready", follow_redirects=False)
    else:
        # Force active status directly for multi-player setup simplicity
        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            game = result.scalar_one()
            game.status = GameStatus.active
            await db.commit()

    return game_id


async def _get_acts(game_id: int) -> list[Act]:
    async with _test_session_factory() as db:
        result = await db.execute(select(Act).where(Act.game_id == game_id).order_by(Act.order))
        return list(result.scalars().all())


async def _get_proposals(game_id: int) -> list[VoteProposal]:
    async with _test_session_factory() as db:
        result = await db.execute(select(VoteProposal).where(VoteProposal.game_id == game_id))
        return list(result.scalars().all())


async def _get_votes(proposal_id: int) -> list[Vote]:
    async with _test_session_factory() as db:
        result = await db.execute(select(Vote).where(Vote.proposal_id == proposal_id))
        return list(result.scalars().all())


async def _get_game(game_id: int) -> Game:
    async with _test_session_factory() as db:
        result = await db.execute(select(Game).where(Game.id == game_id))
        return result.scalar_one()


# ---------------------------------------------------------------------------
# Acts view
# ---------------------------------------------------------------------------


class TestActsView:
    async def test_view_requires_membership(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        await _login(client, 2)
        response = await client.get(f"/games/{game_id}/acts", follow_redirects=False)
        assert response.status_code == 403

    async def test_view_accessible_to_member(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        response = await client.get(f"/games/{game_id}/acts", follow_redirects=False)
        assert response.status_code == 200

    async def test_view_shows_no_acts_message(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        response = await client.get(f"/games/{game_id}/acts", follow_redirects=False)
        assert b"No acts yet" in response.content

    async def test_view_shows_propose_form_when_active(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        response = await client.get(f"/games/{game_id}/acts", follow_redirects=False)
        assert b"Propose a New Act" in response.content

    async def test_view_hides_propose_form_for_setup_game(self, client: AsyncClient) -> None:
        await _login(client, 1)
        r = await client.post(
            "/games", data={"name": "Setup Game", "pitch": "A pitch"}, follow_redirects=False
        )
        game_id = int(r.headers["location"].rsplit("/", 1)[-1])
        response = await client.get(f"/games/{game_id}/acts", follow_redirects=False)
        assert b"Propose a New Act" not in response.content


# ---------------------------------------------------------------------------
# Propose act — single player (auto-approval)
# ---------------------------------------------------------------------------


class TestProposeActSinglePlayer:
    async def test_creates_act_in_active_status(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who betrayed the guild?"},
            follow_redirects=False,
        )
        acts = await _get_acts(game_id)
        assert len(acts) == 1
        assert acts[0].status == ActStatus.active
        assert acts[0].guiding_question == "Who betrayed the guild?"

    async def test_act_title_is_optional(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "What lurks in the dark?"},
            follow_redirects=False,
        )
        acts = await _get_acts(game_id)
        assert acts[0].title is None

    async def test_act_title_stored_when_provided(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        await client.post(
            f"/games/{game_id}/acts",
            data={"title": "The Betrayal", "guiding_question": "Who betrayed the guild?"},
            follow_redirects=False,
        )
        acts = await _get_acts(game_id)
        assert acts[0].title == "The Betrayal"

    async def test_proposal_auto_approved(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who betrayed the guild?"},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id)
        act_proposals = [p for p in proposals if p.proposal_type == ProposalType.act_proposal]
        assert len(act_proposals) == 1
        assert act_proposals[0].status == ProposalStatus.approved

    async def test_implicit_yes_vote_recorded(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who betrayed the guild?"},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id)
        act_proposals = [p for p in proposals if p.proposal_type == ProposalType.act_proposal]
        votes = await _get_votes(act_proposals[0].id)
        assert len(votes) == 1
        assert votes[0].choice == VoteChoice.yes

    async def test_redirects_to_acts_page(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        response = await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who betrayed the guild?"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == f"/games/{game_id}/acts"

    async def test_act_order_increments(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "First question?"},
            follow_redirects=False,
        )
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Second question?"},
            follow_redirects=False,
        )
        acts = await _get_acts(game_id)
        assert acts[0].order == 1
        assert acts[1].order == 2


# ---------------------------------------------------------------------------
# Propose act — multi-player (vote required)
# ---------------------------------------------------------------------------


class TestProposeActMultiPlayer:
    async def test_act_starts_proposed(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client, extra_members=[2])
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who controls the city?"},
            follow_redirects=False,
        )
        acts = await _get_acts(game_id)
        assert acts[0].status == ActStatus.proposed

    async def test_proposal_remains_open(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client, extra_members=[2])
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who controls the city?"},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id)
        act_proposals = [p for p in proposals if p.proposal_type == ProposalType.act_proposal]
        assert act_proposals[0].status == ProposalStatus.open

    async def test_second_yes_vote_activates_act(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client, extra_members=[2])
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who controls the city?"},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id)
        act_proposals = [p for p in proposals if p.proposal_type == ProposalType.act_proposal]
        proposal_id = act_proposals[0].id

        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )

        acts = await _get_acts(game_id)
        assert acts[0].status == ActStatus.active

    async def test_vote_redirects_to_acts_page(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client, extra_members=[2])
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who controls the city?"},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id)
        act_proposals = [p for p in proposals if p.proposal_type == ProposalType.act_proposal]
        proposal_id = act_proposals[0].id

        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == f"/games/{game_id}/acts"

    async def test_approving_act_completes_current_active_act(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client, extra_members=[2])
        await _login(client, 1)

        # First act — auto would require 2 yes, but with 2 players we need both
        # Activate first act directly
        async with _test_session_factory() as db:
            act1 = Act(
                game_id=game_id,
                guiding_question="First act question?",
                status=ActStatus.active,
                order=1,
            )
            db.add(act1)
            await db.commit()

        # Propose second act
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Second act question?"},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id)
        act_proposals = [p for p in proposals if p.proposal_type == ProposalType.act_proposal]
        proposal_id = act_proposals[0].id

        # Bob votes yes → approved
        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )

        acts = await _get_acts(game_id)
        assert acts[0].status == ActStatus.complete
        assert acts[1].status == ActStatus.active


# ---------------------------------------------------------------------------
# Validation and guard rails
# ---------------------------------------------------------------------------


class TestProposeActGuards:
    async def test_requires_active_game(self, client: AsyncClient) -> None:
        await _login(client, 1)
        r = await client.post("/games", data={"name": "G", "pitch": "P"}, follow_redirects=False)
        game_id = int(r.headers["location"].rsplit("/", 1)[-1])
        response = await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Does this work?"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_requires_membership(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Am I allowed?"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_rejects_duplicate_open_proposal(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client, extra_members=[2])
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "First proposal"},
            follow_redirects=False,
        )
        response = await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Second proposal"},
            follow_redirects=False,
        )
        assert response.status_code == 409

    async def test_view_hides_form_when_proposal_pending(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client, extra_members=[2])
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Pending proposal"},
            follow_redirects=False,
        )
        response = await client.get(f"/games/{game_id}/acts", follow_redirects=False)
        assert b"Propose a New Act" not in response.content
        assert b"Pending Act Proposal" in response.content
