"""Tests for act creation and voting routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from loom.models import (
    Act,
    ActStatus,
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    ProposalStatus,
    ProposalType,
    Scene,
    SceneStatus,
    Vote,
    VoteChoice,
    VoteProposal,
)


async def _login(client: AsyncClient, user_id: int) -> None:
    await client.post("/dev/login", data={"user_id": str(user_id)}, follow_redirects=False)


async def _create_active_game(
    client: AsyncClient, db, extra_members: list[int] | None = None
) -> int:
    """Create a game, add optional extra members, activate it via propose-ready."""
    await _login(client, 1)
    r = await client.post(
        "/games", data={"name": "Test Game", "pitch": "A pitch"}, follow_redirects=False
    )
    game_id = int(r.headers["location"].rsplit("/", 1)[-1])

    if extra_members:
        for uid in extra_members:
            db.add(GameMember(game_id=game_id, user_id=uid, role=MemberRole.player))
        await db.commit()

    # activate via propose-ready (single player with only Alice auto-approves)
    # if extra members were added, we need to vote them in too — use direct DB manipulation
    if not extra_members:
        await client.post(f"/games/{game_id}/session0/propose-ready", follow_redirects=False)
    else:
        # Force active status directly for multi-player setup simplicity
        db.expire_all()
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one()
        game.status = GameStatus.active
        await db.commit()

    return game_id


async def _get_acts(db, game_id: int) -> list[Act]:
    db.expire_all()
    result = await db.execute(select(Act).where(Act.game_id == game_id).order_by(Act.order))
    return list(result.scalars().all())


async def _get_proposals(db, game_id: int) -> list[VoteProposal]:
    db.expire_all()
    result = await db.execute(select(VoteProposal).where(VoteProposal.game_id == game_id))
    return list(result.scalars().all())


async def _get_votes(db, proposal_id: int) -> list[Vote]:
    db.expire_all()
    result = await db.execute(select(Vote).where(Vote.proposal_id == proposal_id))
    return list(result.scalars().all())


async def _get_game(db, game_id: int) -> Game:
    db.expire_all()
    result = await db.execute(select(Game).where(Game.id == game_id))
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Acts view
# ---------------------------------------------------------------------------


class TestActsView:
    async def test_view_requires_membership(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        await _login(client, 2)
        response = await client.get(f"/games/{game_id}/acts", follow_redirects=False)
        assert response.status_code == 403

    async def test_view_accessible_to_member(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        response = await client.get(f"/games/{game_id}/acts", follow_redirects=False)
        assert response.status_code == 200

    async def test_view_shows_no_acts_message(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        response = await client.get(f"/games/{game_id}/acts", follow_redirects=False)
        assert b"No acts yet" in response.content

    async def test_view_shows_propose_form_when_active(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
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
    async def test_creates_act_in_active_status(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who betrayed the guild?"},
            follow_redirects=False,
        )
        acts = await _get_acts(db, game_id)
        assert len(acts) == 1
        assert acts[0].status == ActStatus.active
        assert acts[0].guiding_question == "Who betrayed the guild?"

    async def test_act_title_is_optional(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "What lurks in the dark?"},
            follow_redirects=False,
        )
        acts = await _get_acts(db, game_id)
        assert acts[0].title is None

    async def test_act_title_stored_when_provided(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        await client.post(
            f"/games/{game_id}/acts",
            data={"title": "The Betrayal", "guiding_question": "Who betrayed the guild?"},
            follow_redirects=False,
        )
        acts = await _get_acts(db, game_id)
        assert acts[0].title == "The Betrayal"

    async def test_proposal_auto_approved(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who betrayed the guild?"},
            follow_redirects=False,
        )
        proposals = await _get_proposals(db, game_id)
        act_proposals = [p for p in proposals if p.proposal_type == ProposalType.act_proposal]
        assert len(act_proposals) == 1
        assert act_proposals[0].status == ProposalStatus.approved

    async def test_implicit_yes_vote_recorded(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who betrayed the guild?"},
            follow_redirects=False,
        )
        proposals = await _get_proposals(db, game_id)
        act_proposals = [p for p in proposals if p.proposal_type == ProposalType.act_proposal]
        proposal_id = act_proposals[0].id
        votes = await _get_votes(db, proposal_id)
        assert len(votes) == 1
        assert votes[0].choice == VoteChoice.yes

    async def test_redirects_to_acts_page(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        response = await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who betrayed the guild?"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == f"/games/{game_id}/acts"

    async def test_act_order_increments(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
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
        acts = await _get_acts(db, game_id)
        assert acts[0].order == 1
        assert acts[1].order == 2


# ---------------------------------------------------------------------------
# Propose act — multi-player (vote required)
# ---------------------------------------------------------------------------


class TestProposeActMultiPlayer:
    async def test_act_starts_proposed(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who controls the city?"},
            follow_redirects=False,
        )
        acts = await _get_acts(db, game_id)
        assert acts[0].status == ActStatus.proposed

    async def test_proposal_remains_open(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who controls the city?"},
            follow_redirects=False,
        )
        proposals = await _get_proposals(db, game_id)
        act_proposals = [p for p in proposals if p.proposal_type == ProposalType.act_proposal]
        assert act_proposals[0].status == ProposalStatus.open

    async def test_second_yes_vote_activates_act(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who controls the city?"},
            follow_redirects=False,
        )
        proposals = await _get_proposals(db, game_id)
        act_proposals = [p for p in proposals if p.proposal_type == ProposalType.act_proposal]
        proposal_id = act_proposals[0].id

        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )

        acts = await _get_acts(db, game_id)
        assert acts[0].status == ActStatus.active

    async def test_vote_redirects_to_acts_page(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Who controls the city?"},
            follow_redirects=False,
        )
        proposals = await _get_proposals(db, game_id)
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

    async def test_approving_act_completes_current_active_act(
        self, client: AsyncClient, db
    ) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)

        # First act — activate directly
        act1 = Act(
            game_id=game_id,
            guiding_question="First act question?",
            status=ActStatus.active,
            order=1,
        )
        db.add(act1)
        await db.commit()
        act1_id = act1.id  # capture before any expire_all

        # Propose second act
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Second act question?"},
            follow_redirects=False,
        )
        proposals = await _get_proposals(db, game_id)
        act_proposals = [p for p in proposals if p.proposal_type == ProposalType.act_proposal]
        proposal_id = act_proposals[0].id

        # Bob votes yes → approved
        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )

        acts = await _get_acts(db, game_id)
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

    async def test_requires_membership(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Am I allowed?"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_rejects_duplicate_open_proposal(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
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

    async def test_view_hides_form_when_proposal_pending(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts",
            data={"guiding_question": "Pending proposal"},
            follow_redirects=False,
        )
        response = await client.get(f"/games/{game_id}/acts", follow_redirects=False)
        assert b"Propose a New Act" not in response.content
        assert b"Pending Act Proposal" in response.content


# ---------------------------------------------------------------------------
# Act completion
# ---------------------------------------------------------------------------


async def _create_active_act_direct(db, game_id: int) -> int:
    """Insert an active act directly into the DB."""
    act = Act(
        game_id=game_id,
        guiding_question="What is at stake?",
        status=ActStatus.active,
        order=1,
    )
    db.add(act)
    await db.commit()
    return act.id


async def _get_act(db, act_id: int) -> Act:
    db.expire_all()
    result = await db.execute(select(Act).where(Act.id == act_id))
    return result.scalar_one()


async def _create_active_scene_for_act(db, act_id: int, game_id: int) -> int:
    scene = Scene(
        act_id=act_id,
        guiding_question="A scene",
        tension=5,
        status=SceneStatus.active,
        order=1,
    )
    db.add(scene)
    await db.commit()
    return scene.id


async def _get_scene_direct(db, scene_id: int) -> Scene:
    db.expire_all()
    result = await db.execute(select(Scene).where(Scene.id == scene_id))
    return result.scalar_one()


class TestActCompletion:
    async def test_single_player_auto_approves(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act_direct(db, game_id)

        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/complete",
            follow_redirects=False,
        )
        assert r.status_code == 303

        act = await _get_act(db, act_id)
        assert act.status == ActStatus.complete

    async def test_single_player_proposal_approved(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act_direct(db, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/complete",
            follow_redirects=False,
        )
        proposals = await _get_proposals(db, game_id)
        completion_proposals = [
            p for p in proposals if p.proposal_type == ProposalType.act_complete
        ]
        assert len(completion_proposals) == 1
        assert completion_proposals[0].status == ProposalStatus.approved

    async def test_completes_active_scene_on_approval(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act_direct(db, game_id)
        scene_id = await _create_active_scene_for_act(db, act_id, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/complete",
            follow_redirects=False,
        )
        scene = await _get_scene_direct(db, scene_id)
        assert scene.status == SceneStatus.complete

    async def test_multi_player_stays_pending(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act_direct(db, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/complete",
            follow_redirects=False,
        )
        act = await _get_act(db, act_id)
        assert act.status == ActStatus.active

        proposals = await _get_proposals(db, game_id)
        completion = next(p for p in proposals if p.proposal_type == ProposalType.act_complete)
        assert completion.status == ProposalStatus.open

    async def test_multi_player_vote_approves(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act_direct(db, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/complete",
            follow_redirects=False,
        )
        proposals = await _get_proposals(db, game_id)
        proposal = next(p for p in proposals if p.proposal_type == ProposalType.act_complete)
        proposal_id = proposal.id

        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )
        act = await _get_act(db, act_id)
        assert act.status == ActStatus.complete

    async def test_duplicate_proposal_rejected(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act_direct(db, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/complete",
            follow_redirects=False,
        )
        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/complete",
            follow_redirects=False,
        )
        assert r.status_code == 409

    async def test_cannot_complete_non_active_act(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        act = Act(
            game_id=game_id,
            guiding_question="Proposed?",
            status=ActStatus.proposed,
            order=1,
        )
        db.add(act)
        await db.commit()
        act_id = act.id  # capture before any expire_all

        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/complete",
            follow_redirects=False,
        )
        assert r.status_code == 403

    async def test_scenes_page_accessible_after_act_complete(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act_direct(db, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/complete",
            follow_redirects=False,
        )
        r = await client.get(f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False)
        assert r.status_code == 200

    async def test_propose_button_on_scenes_page(self, client: AsyncClient, db) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act_direct(db, game_id)

        r = await client.get(f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False)
        assert b"Propose Act Completion" in r.content


# ---------------------------------------------------------------------------
# Act narrative compilation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestActNarrative:
    async def test_narrative_generated_on_auto_approve(self, client: AsyncClient, db) -> None:
        """Single-player act completion triggers act narrative generation."""
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act_direct(db, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/complete",
            follow_redirects=False,
        )

        db.expire_all()
        act = await _get_act(db, act_id)
        assert act.narrative is not None
        assert len(act.narrative) > 0

    async def test_narrative_skipped_when_disabled(self, client: AsyncClient, db) -> None:
        """auto_generate_narrative=False suppresses act narrative generation."""
        game_id = await _create_active_game(client, db)

        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one()
        game.auto_generate_narrative = False
        await db.commit()

        act_id = await _create_active_act_direct(db, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/complete",
            follow_redirects=False,
        )

        db.expire_all()
        act = await _get_act(db, act_id)
        assert act.narrative is None

    async def test_narrative_generated_on_vote_approval(self, client: AsyncClient, db) -> None:
        """Vote-approved act completion triggers act narrative generation."""
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act_direct(db, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/complete",
            follow_redirects=False,
        )
        proposals = await _get_proposals(db, game_id)
        proposal = next(p for p in proposals if p.proposal_type == ProposalType.act_complete)
        proposal_id = proposal.id

        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )

        db.expire_all()
        act = await _get_act(db, act_id)
        assert act.narrative is not None
        assert len(act.narrative) > 0

    async def test_narrative_shown_on_scenes_page(self, client: AsyncClient, db) -> None:
        """Completed act with narrative shows it on the scenes list page."""
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act_direct(db, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/complete",
            follow_redirects=False,
        )

        r = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes",
            follow_redirects=False,
        )
        assert b"Act Narrative" in r.content
