"""Tests for scene creation and voting routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from loom.models import (
    Act,
    ActStatus,
    Beat,
    BeatComment,
    BeatStatus,
    Character,
    EventType,
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    Notification,
    NotificationType,
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
    client: AsyncClient, db: AsyncSession, extra_members: list[int] | None = None
) -> int:
    """Create a game, add optional extra members, activate it."""
    await _login(client, 1)
    r = await client.post(
        "/games", data={"name": "Test Game", "pitch": "A pitch"}, follow_redirects=False
    )
    game_id = int(r.headers["location"].rsplit("/", 1)[-1])

    if extra_members:
        for uid in extra_members:
            db.add(GameMember(game_id=game_id, user_id=uid, role=MemberRole.player))
        await db.commit()

    if not extra_members:
        await client.post(f"/games/{game_id}/session0/propose-ready", follow_redirects=False)
    else:
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one()
        game.status = GameStatus.active
        await db.commit()

    return game_id


async def _create_active_act(game_id: int, db: AsyncSession) -> int:
    """Insert an active act directly and return its id."""
    act = Act(
        game_id=game_id,
        guiding_question="What is at stake?",
        status=ActStatus.active,
        order=1,
    )
    db.add(act)
    await db.commit()
    return act.id


async def _create_character(
    game_id: int, owner_id: int, db: AsyncSession, name: str = "Hero"
) -> int:
    """Insert a character and return its id."""
    char = Character(game_id=game_id, owner_id=owner_id, name=name)
    db.add(char)
    await db.commit()
    return char.id


async def _get_scenes(act_id: int, db: AsyncSession) -> list[Scene]:
    db.expire_all()
    result = await db.execute(select(Scene).where(Scene.act_id == act_id).order_by(Scene.order))
    return list(result.scalars().all())


async def _get_scene_character_ids(scene_id: int, db: AsyncSession) -> list[int]:
    db.expire_all()
    result = await db.execute(
        select(Scene).where(Scene.id == scene_id).options(selectinload(Scene.characters_present))
    )
    scene = result.scalar_one()
    return [c.id for c in scene.characters_present]


async def _get_proposals(game_id: int, db: AsyncSession) -> list[VoteProposal]:
    db.expire_all()
    result = await db.execute(select(VoteProposal).where(VoteProposal.game_id == game_id))
    return list(result.scalars().all())


async def _get_votes(proposal_id: int, db: AsyncSession) -> list[Vote]:
    db.expire_all()
    result = await db.execute(select(Vote).where(Vote.proposal_id == proposal_id))
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Scenes view
# ---------------------------------------------------------------------------


class TestScenesView:
    async def test_view_requires_membership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        await _login(client, 2)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_view_accessible_to_member(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False
        )
        assert response.status_code == 200

    async def test_view_404_for_unknown_act(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        response = await client.get(f"/games/{game_id}/acts/9999/scenes", follow_redirects=False)
        assert response.status_code == 404

    async def test_view_403_for_non_active_act(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act = Act(
            game_id=game_id,
            guiding_question="Proposed act?",
            status=ActStatus.proposed,
            order=1,
        )
        db.add(act)
        await db.commit()
        act_id = act.id
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_view_shows_no_scenes_message(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False
        )
        assert b"No scenes yet" in response.content

    async def test_view_shows_propose_form_when_active(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False
        )
        assert b"Propose a New Scene" in response.content

    async def test_view_hides_form_when_proposal_pending(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Pending scene?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False
        )
        assert b"Propose a New Scene" not in response.content
        assert b"Pending Scene Proposal" in response.content


# ---------------------------------------------------------------------------
# Propose scene — single player (auto-approval)
# ---------------------------------------------------------------------------


class TestProposeSceneSinglePlayer:
    async def test_creates_scene_in_active_status(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id, db)
        assert len(scenes) == 1
        assert scenes[0].status == SceneStatus.active
        assert scenes[0].guiding_question == "Will they escape?"

    async def test_scene_location_optional(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id, db)
        assert scenes[0].location is None

    async def test_scene_location_stored(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={
                "guiding_question": "Will they escape?",
                "location": "The Vault",
                "character_ids": str(char_id),
            },
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id, db)
        assert scenes[0].location == "The Vault"

    async def test_scene_tension_stored(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={
                "guiding_question": "Will they escape?",
                "tension": "7",
                "character_ids": str(char_id),
            },
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id, db)
        assert scenes[0].tension == 7

    async def test_tension_defaults_to_5(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id, db)
        assert scenes[0].tension == 5

    async def test_characters_present_stored(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id, db)
        char_ids = await _get_scene_character_ids(scenes[0].id, db)
        assert char_id in char_ids

    async def test_proposal_auto_approved(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id, db)
        scene_proposals = [p for p in proposals if p.proposal_type == ProposalType.scene_proposal]
        assert len(scene_proposals) == 1
        assert scene_proposals[0].status == ProposalStatus.approved

    async def test_implicit_yes_vote_recorded(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id, db)
        scene_proposals = [p for p in proposals if p.proposal_type == ProposalType.scene_proposal]
        votes = await _get_votes(scene_proposals[0].id, db)
        assert len(votes) == 1
        assert votes[0].choice == VoteChoice.yes

    async def test_redirects_to_scenes_page(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == f"/games/{game_id}/acts/{act_id}/scenes"

    async def test_scene_order_increments(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "First scene?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Second scene?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id, db)
        assert scenes[0].order == 1
        assert scenes[1].order == 2

    async def test_active_scene_completed_when_new_approved(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "First scene?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Second scene?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id, db)
        assert scenes[0].status == SceneStatus.complete
        assert scenes[1].status == SceneStatus.active


# ---------------------------------------------------------------------------
# Propose scene — multi-player (vote required)
# ---------------------------------------------------------------------------


class TestProposeSceneMultiPlayer:
    async def test_scene_starts_proposed(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Who controls the vault?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id, db)
        assert scenes[0].status == SceneStatus.proposed

    async def test_proposal_remains_open(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Who controls the vault?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id, db)
        scene_proposals = [p for p in proposals if p.proposal_type == ProposalType.scene_proposal]
        assert scene_proposals[0].status == ProposalStatus.open

    async def test_second_yes_vote_activates_scene(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Who controls the vault?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id, db)
        scene_proposals = [p for p in proposals if p.proposal_type == ProposalType.scene_proposal]
        proposal_id = scene_proposals[0].id

        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )

        scenes = await _get_scenes(act_id, db)
        assert scenes[0].status == SceneStatus.active

    async def test_vote_redirects_to_scenes_page(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Who controls the vault?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id, db)
        scene_proposals = [p for p in proposals if p.proposal_type == ProposalType.scene_proposal]
        proposal_id = scene_proposals[0].id

        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == f"/games/{game_id}/acts/{act_id}/scenes"


# ---------------------------------------------------------------------------
# Validation and guard rails
# ---------------------------------------------------------------------------


class TestProposeSceneGuards:
    async def test_requires_active_game(self, client: AsyncClient, db: AsyncSession) -> None:
        await _login(client, 1)
        r = await client.post("/games", data={"name": "G", "pitch": "P"}, follow_redirects=False)
        game_id = int(r.headers["location"].rsplit("/", 1)[-1])
        # Insert an act directly to bypass game status check on act lookup
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)
        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Does this work?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_requires_active_act(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act = Act(
            game_id=game_id,
            guiding_question="Proposed act?",
            status=ActStatus.proposed,
            order=1,
        )
        db.add(act)
        await db.commit()
        act_id = act.id
        char_id = await _create_character(game_id, 1, db)
        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will this work?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_requires_membership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Am I allowed?", "character_ids": "1"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_requires_guiding_question(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)
        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "   ", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_requires_at_least_one_character(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?"},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_rejects_character_from_another_game(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)

        # Create a second game and a character in it
        r2 = await client.post(
            "/games", data={"name": "Other Game", "pitch": "P"}, follow_redirects=False
        )
        other_game_id = int(r2.headers["location"].rsplit("/", 1)[-1])
        other_char_id = await _create_character(other_game_id, 1, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(other_char_id)},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_rejects_invalid_tension_low(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)
        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={
                "guiding_question": "Will they escape?",
                "tension": "0",
                "character_ids": str(char_id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_rejects_invalid_tension_high(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)
        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={
                "guiding_question": "Will they escape?",
                "tension": "10",
                "character_ids": str(char_id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_rejects_duplicate_open_proposal(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "First proposal", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Second proposal", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# Scene detail view
# ---------------------------------------------------------------------------


async def _create_active_scene(act_id: int, game_id: int, db: AsyncSession) -> int:
    """Insert an active scene with a character and return its id."""
    char = Character(game_id=game_id, owner_id=1, name="Test Hero")
    db.add(char)
    await db.flush()
    scene = Scene(
        act_id=act_id,
        guiding_question="What is at stake?",
        tension=6,
        status=SceneStatus.active,
        order=1,
    )
    db.add(scene)
    await db.flush()
    await db.refresh(scene, ["characters_present"])
    scene.characters_present = [char]
    await db.commit()
    return scene.id


class TestSceneDetailView:
    async def test_accessible_to_member(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", follow_redirects=False
        )
        assert response.status_code == 200

    async def test_requires_membership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)
        await _login(client, 2)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_404_for_unknown_scene(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/9999", follow_redirects=False
        )
        assert response.status_code == 404

    async def test_shows_scene_info(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", follow_redirects=False
        )
        assert b"What is at stake?" in response.content
        assert b"Tension" in response.content

    async def test_shows_empty_beat_timeline(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", follow_redirects=False
        )
        assert b"No beats yet" in response.content

    async def test_shows_filter_controls(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", follow_redirects=False
        )
        assert b"IC Only" in response.content
        assert b"OOC Only" in response.content

    async def test_htmx_polling_attr_present(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", follow_redirects=False
        )
        assert b"hx-trigger" in response.content
        assert b"every 5s" in response.content

    async def test_filter_query_param_accepted(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)
        for f in ("all", "ic", "ooc"):
            response = await client.get(
                f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}?filter={f}",
                follow_redirects=False,
            )
            assert response.status_code == 200

    async def test_default_tension_uses_last_scene_tension(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char_id = await _create_character(game_id, 1, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={
                "guiding_question": "First scene?",
                "tension": "7",
                "character_ids": str(char_id),
            },
            follow_redirects=False,
        )
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False
        )
        # The propose form should pre-fill with the last scene's tension (7)
        assert b'value="7"' in response.content


# ---------------------------------------------------------------------------
# Beats partial
# ---------------------------------------------------------------------------


class TestBeatsPartial:
    async def test_returns_200_for_member(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats", follow_redirects=False
        )
        assert response.status_code == 200

    async def test_requires_membership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)
        await _login(client, 2)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_404_for_unknown_scene(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/9999/beats", follow_redirects=False
        )
        assert response.status_code == 404

    async def test_shows_empty_message(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats", follow_redirects=False
        )
        assert b"No beats yet" in response.content

    async def test_filter_param_accepted(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)
        for f in ("all", "ic", "ooc"):
            response = await client.get(
                f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats?filter={f}",
                follow_redirects=False,
            )
            assert response.status_code == 200


# ---------------------------------------------------------------------------
# Beat submission
# ---------------------------------------------------------------------------


async def _get_beats(scene_id: int, db: AsyncSession) -> list[Beat]:
    db.expire_all()
    result = await db.execute(
        select(Beat)
        .where(Beat.scene_id == scene_id)
        .options(selectinload(Beat.events))
        .order_by(Beat.order)
    )
    return list(result.scalars().all())


def _narrative_data(content: str) -> dict:
    """Build form data for a single narrative event."""
    return {"event_type": "narrative", "event_content": content}


# ---------------------------------------------------------------------------
# Beat consistency check (REQ-BEAT-005)
# ---------------------------------------------------------------------------


class TestCheckBeat:
    async def test_returns_empty_flags_for_clean_beat(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/check",
            data={"event_type": "narrative", "event_content": "The hero steps forward."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data == {"flags": []}

    async def test_returns_flags_when_ai_finds_issues(
        self, client: AsyncClient, monkeypatch, db: AsyncSession
    ) -> None:
        async def _flagging_check(
            game, scene, beat_text, roll_results=None, *, db=None, game_id=None
        ):
            return ["You rolled a partial success but this reads like a full success."]

        monkeypatch.setattr("loom.routers.scenes.check_beat_consistency", _flagging_check)

        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/check",
            data={"event_type": "narrative", "event_content": "Everything goes perfectly."},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["flags"]) == 1
        assert "partial success" in data["flags"][0]

    async def test_ooc_only_beat_returns_empty_flags(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/check",
            data={"event_type": "ooc", "event_content": "Should we take a break?"},
        )
        assert response.status_code == 200
        assert response.json() == {"flags": []}

    async def test_requires_membership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)
        await _login(client, 2)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/check",
            data={"event_type": "narrative", "event_content": "Action."},
        )
        assert response.status_code == 403

    async def test_ai_failure_returns_empty_flags(
        self, client: AsyncClient, monkeypatch, db: AsyncSession
    ) -> None:
        async def _exploding_check(
            game, scene, beat_text, roll_results=None, *, db=None, game_id=None
        ):
            raise RuntimeError("AI is down")

        monkeypatch.setattr("loom.routers.scenes.check_beat_consistency", _exploding_check)

        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/check",
            data={"event_type": "narrative", "event_content": "The hero acts bravely."},
        )
        assert response.status_code == 200
        assert response.json() == {"flags": []}

    async def test_404_for_wrong_scene(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/9999/beats/check",
            data={"event_type": "narrative", "event_content": "Action."},
        )
        assert response.status_code == 404


class TestSubmitBeat:
    async def test_creates_beat_with_narrative_event(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("The hero steps forward."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        assert len(beats) == 1
        assert len(beats[0].events) == 1
        assert beats[0].events[0].content == "The hero steps forward."

    async def test_beat_is_immediately_canon(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Action."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        assert beats[0].status == BeatStatus.canon

    async def test_event_type_is_narrative(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Action."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        assert beats[0].events[0].type == EventType.narrative

    async def test_beat_order_increments(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("First."),
            follow_redirects=False,
        )
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Second."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        assert beats[0].order == 1
        assert beats[1].order == 2

    async def test_redirects_to_scene_detail(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Action."),
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == (f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}")

    async def test_requires_membership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)
        await _login(client, 2)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Sneaky."),
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_rejects_empty_content(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("   "),
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_rejects_beat_on_inactive_scene(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene = Scene(
            act_id=act_id,
            guiding_question="Done?",
            tension=5,
            status=SceneStatus.complete,
            order=1,
        )
        db.add(scene)
        await db.commit()
        scene_id = scene.id

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Too late."),
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_beat_appears_in_timeline(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("A dramatic entrance."),
            follow_redirects=False,
        )
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            follow_redirects=False,
        )
        assert b"A dramatic entrance." in response.content

    async def test_form_shown_for_active_scene(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}",
            follow_redirects=False,
        )
        assert b"Submit Beat" in response.content

    async def test_rejects_no_events(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_rejects_invalid_event_type(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={"event_type": "oracle", "event_content": "Something"},
            follow_redirects=False,
        )
        assert response.status_code == 422


class TestSubmitBeatMultiEvent:
    async def test_ooc_event_stored(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={"event_type": "ooc", "event_content": "Does this trigger a safety tool?"},
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        assert len(beats) == 1
        assert beats[0].events[0].type == EventType.ooc
        assert beats[0].events[0].content == "Does this trigger a safety tool?"

    async def test_roll_event_stored(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={
                "event_type": "roll",
                "event_notation": "2d6+3",
                "event_reason": "Climbing the wall",
            },
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        assert len(beats) == 1
        ev = beats[0].events[0]
        assert ev.type == EventType.roll
        assert ev.roll_notation == "2d6+3"
        assert ev.content == "Climbing the wall"
        # 2d6+3: min=5, max=15
        assert ev.roll_result is not None
        assert 5 <= ev.roll_result <= 15

    async def test_roll_without_reason(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={"event_type": "roll", "event_notation": "1d20"},
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        ev = beats[0].events[0]
        assert ev.roll_notation == "1d20"
        assert ev.content is None
        assert ev.roll_result is not None
        assert 1 <= ev.roll_result <= 20

    async def test_roll_invalid_notation_rejected(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={"event_type": "roll", "event_notation": "roll some dice"},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_roll_requires_notation(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={"event_type": "roll", "event_notation": ""},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_multi_event_beat_stored_in_order(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={
                "event_type": ["narrative", "roll", "ooc"],
                "event_content": ["She draws her sword.", "", "Should this trigger tension?"],
                "event_notation": ["", "2d6", ""],
                "event_reason": ["", "Attack", ""],
            },
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        assert len(beats) == 1
        events = beats[0].events
        assert len(events) == 3
        assert events[0].type == EventType.narrative
        assert events[0].order == 1
        assert events[1].type == EventType.roll
        assert events[1].order == 2
        assert events[1].roll_notation == "2d6"
        assert events[2].type == EventType.ooc
        assert events[2].order == 3

    async def test_multi_event_all_appear_in_timeline(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={
                "event_type": ["narrative", "ooc"],
                "event_content": ["The vault door slides open.", "Was that too easy?"],
            },
            follow_redirects=False,
        )
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            follow_redirects=False,
        )
        assert b"The vault door slides open." in response.content
        assert b"Was that too easy?" in response.content


# ---------------------------------------------------------------------------
# Beat significance classification
# ---------------------------------------------------------------------------


class TestBeatSignificanceClassification:
    async def test_minor_beat_is_immediately_canon(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={
                "event_type": "narrative",
                "event_content": "A minor thing happens.",
                "beat_significance": "minor",
            },
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        assert beats[0].significance.value == "minor"
        assert beats[0].status == BeatStatus.canon

    async def test_major_beat_enters_proposed_status(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        # Needs 2 players: proposer's implicit yes (1/2) does not meet threshold (>1).
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={
                "event_type": "narrative",
                "event_content": "A major revelation.",
                "beat_significance": "major",
            },
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        assert beats[0].significance.value == "major"
        assert beats[0].status == BeatStatus.proposed

    async def test_major_beat_single_player_auto_approves(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        # Single-player: proposer's implicit yes (1/1) exceeds threshold (>0.5) → auto-canon.
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={
                "event_type": "narrative",
                "event_content": "A solo revelation.",
                "beat_significance": "major",
            },
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        assert beats[0].significance.value == "major"
        assert beats[0].status == BeatStatus.canon

    async def test_default_significance_is_minor(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        """No beat_significance field defaults to minor (AI stub always returns minor)."""
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Something happens."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        assert beats[0].significance.value == "minor"
        assert beats[0].status == BeatStatus.canon

    async def test_invalid_significance_rejected(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={"event_type": "narrative", "event_content": "Text.", "beat_significance": "huge"},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_form_shows_significance_selector(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}",
            follow_redirects=False,
        )
        assert b"beat_significance" in response.content
        assert b"Minor" in response.content
        assert b"Major" in response.content
        assert b"AI suggests" in response.content


# ---------------------------------------------------------------------------
# Scene completion
# ---------------------------------------------------------------------------


async def _get_scene(scene_id: int, db: AsyncSession) -> Scene:
    db.expire_all()
    result = await db.execute(select(Scene).where(Scene.id == scene_id))
    return result.scalar_one()


class TestSceneCompletion:
    async def test_single_player_auto_approves(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/complete",
            follow_redirects=False,
        )
        assert r.status_code == 303

        scene = await _get_scene(scene_id, db)
        assert scene.status == SceneStatus.complete

    async def test_single_player_proposal_approved(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/complete",
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id, db)
        completion_proposals = [
            p for p in proposals if p.proposal_type == ProposalType.scene_complete
        ]
        assert len(completion_proposals) == 1
        assert completion_proposals[0].status == ProposalStatus.approved

    async def test_multi_player_stays_pending(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/complete",
            follow_redirects=False,
        )
        scene = await _get_scene(scene_id, db)
        assert scene.status == SceneStatus.active

        proposals = await _get_proposals(game_id, db)
        completion = next(p for p in proposals if p.proposal_type == ProposalType.scene_complete)
        assert completion.status == ProposalStatus.open

    async def test_multi_player_vote_approves(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/complete",
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id, db)
        proposal = next(p for p in proposals if p.proposal_type == ProposalType.scene_complete)

        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal.id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )
        scene = await _get_scene(scene_id, db)
        assert scene.status == SceneStatus.complete

    async def test_duplicate_proposal_rejected(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/complete",
            follow_redirects=False,
        )
        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/complete",
            follow_redirects=False,
        )
        assert r.status_code == 409

    async def test_cannot_complete_non_active_scene(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        char = Character(game_id=game_id, owner_id=1, name="Hero")
        db.add(char)
        await db.flush()
        scene = Scene(
            act_id=act_id,
            guiding_question="Already done?",
            tension=5,
            status=SceneStatus.complete,
            order=1,
        )
        db.add(scene)
        await db.commit()
        scene_id = scene.id

        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/complete",
            follow_redirects=False,
        )
        assert r.status_code == 403

    async def test_beat_submission_blocked_for_complete_scene(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        # Complete the scene (auto-approved for single player)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/complete",
            follow_redirects=False,
        )

        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={"event_type": "narrative", "event_content": "A beat"},
            follow_redirects=False,
        )
        assert r.status_code == 403

    async def test_page_shows_complete_status(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/complete",
            follow_redirects=False,
        )
        r = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", follow_redirects=False
        )
        assert r.status_code == 200
        assert b"Complete" in r.content

    async def test_scenes_page_links_completed_scene(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/complete",
            follow_redirects=False,
        )
        r = await client.get(f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False)
        assert r.status_code == 200
        assert f"/scenes/{scene_id}".encode() in r.content


# ---------------------------------------------------------------------------
# Challenge a beat
# ---------------------------------------------------------------------------


async def _get_notifications(user_id: int, db: AsyncSession) -> list[Notification]:
    db.expire_all()
    result = await db.execute(select(Notification).where(Notification.user_id == user_id))
    return list(result.scalars().all())


class TestChallengeBeat:
    async def test_member_can_challenge_canon_beat(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        # User 1 submits a minor (auto-canon) beat
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("The hero strides in."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        assert beats[0].status == BeatStatus.canon

        # User 2 challenges it
        await _login(client, 2)
        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beats[0].id}/challenge",
            data={"reason": "This contradicts established lore."},
            follow_redirects=False,
        )
        assert r.status_code == 303

        beats = await _get_beats(scene_id, db)
        assert beats[0].status == BeatStatus.challenged
        assert beats[0].challenge_reason == "This contradicts established lore."
        assert beats[0].challenged_by_id == 2

    async def test_author_notified_on_challenge(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("A moment of silence."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        beat_id = beats[0].id

        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/challenge",
            data={"reason": "Inconsistent with act 1."},
            follow_redirects=False,
        )

        notifications = await _get_notifications(1, db)
        assert any(n.notification_type == NotificationType.beat_challenged for n in notifications)
        assert any("challenged your beat" in n.message for n in notifications)

    async def test_non_member_cannot_challenge(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Something happens."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)

        await _login(client, 2)
        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beats[0].id}/challenge",
            data={"reason": "Does not make sense."},
            follow_redirects=False,
        )
        assert r.status_code == 403

    async def test_cannot_challenge_non_canon_beat(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2, 3])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        # Submit a major beat (proposed, not canon)
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={
                "event_type": "narrative",
                "event_content": "Big event.",
                "beat_significance": "major",
            },
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        assert beats[0].status == BeatStatus.proposed

        await _login(client, 2)
        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beats[0].id}/challenge",
            data={"reason": "This is not how magic works."},
            follow_redirects=False,
        )
        assert r.status_code == 400

    async def test_empty_reason_rejected(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Something happens."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)

        await _login(client, 2)
        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beats[0].id}/challenge",
            data={"reason": "   "},
            follow_redirects=False,
        )
        assert r.status_code == 400

    async def test_author_challenging_own_beat_no_self_notification(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("I made a mistake."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)

        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beats[0].id}/challenge",
            data={"reason": "I contradicted earlier lore."},
            follow_redirects=False,
        )
        assert r.status_code == 303

        # Beat transitions to challenged
        beats = await _get_beats(scene_id, db)
        assert beats[0].status == BeatStatus.challenged

        # No self-notification
        notifications = await _get_notifications(1, db)
        assert not any(
            n.notification_type == NotificationType.beat_challenged and "your beat" in n.message
            for n in notifications
        )


# ---------------------------------------------------------------------------
# Challenge resolution
# ---------------------------------------------------------------------------


async def _get_beat_comments(beat_id: int, db: AsyncSession) -> list[BeatComment]:
    db.expire_all()
    result = await db.execute(select(BeatComment).where(BeatComment.beat_id == beat_id))
    return list(result.scalars().all())


async def _challenge_beat(
    client: AsyncClient,
    game_id: int,
    act_id: int,
    scene_id: int,
    beat_id: int,
    challenger_user_id: int,
    reason: str = "This contradicts the established lore.",
) -> None:
    """Helper: log in as challenger and file a challenge."""
    await _login(client, challenger_user_id)
    await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/challenge",
        data={"reason": reason},
        follow_redirects=False,
    )


@pytest.mark.anyio
class TestChallengeResolution:
    async def test_author_can_accept_challenge(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("The hero enters the tavern."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        beat_id = beats[0].id

        await _challenge_beat(client, game_id, act_id, scene_id, beat_id, challenger_user_id=2)

        await _login(client, 1)
        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/challenge/accept",
            data={"content": "The hero slips quietly into the tavern."},
            follow_redirects=False,
        )
        assert r.status_code == 303

        beats = await _get_beats(scene_id, db)
        assert beats[0].status == BeatStatus.proposed
        assert beats[0].challenge_outcome == "accepted_revision"
        # challenge_reason and challenged_by_id are preserved for history display
        assert beats[0].challenge_reason is not None
        assert beats[0].challenged_by_id is not None

    async def test_accept_replaces_narrative_events(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Original content."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        beat_id = beats[0].id

        await _challenge_beat(client, game_id, act_id, scene_id, beat_id, challenger_user_id=2)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/challenge/accept",
            data={"content": "Revised content."},
            follow_redirects=False,
        )

        beats = await _get_beats(scene_id, db)
        narrative_events = [e for e in beats[0].events if e.type == EventType.narrative]
        assert len(narrative_events) == 1
        assert narrative_events[0].content == "Revised content."

    async def test_accept_creates_beat_proposal(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Some event."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        beat_id = beats[0].id

        await _challenge_beat(client, game_id, act_id, scene_id, beat_id, challenger_user_id=2)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/challenge/accept",
            data={"content": "Revised event."},
            follow_redirects=False,
        )

        proposals = await _get_proposals(game_id, db)
        beat_proposals = [
            p
            for p in proposals
            if p.proposal_type == ProposalType.beat_proposal and p.beat_id == beat_id
        ]
        assert len(beat_proposals) == 1
        assert beat_proposals[0].status == ProposalStatus.open

    async def test_accept_single_player_auto_approves(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        # Single-player: author's implicit yes (1/1) exceeds threshold → auto-canon.
        game_id = await _create_active_game(client, db)
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Something happened."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        beat_id = beats[0].id

        # Author challenges their own beat
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/challenge",
            data={"reason": "I changed my mind."},
            follow_redirects=False,
        )

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/challenge/accept",
            data={"content": "Better version."},
            follow_redirects=False,
        )

        beats = await _get_beats(scene_id, db)
        assert beats[0].status == BeatStatus.canon

    async def test_non_author_cannot_accept(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Something."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        beat_id = beats[0].id

        await _challenge_beat(client, game_id, act_id, scene_id, beat_id, challenger_user_id=2)

        # Challenger tries to accept (should fail)
        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/challenge/accept",
            data={"content": "Changed by challenger."},
            follow_redirects=False,
        )
        assert r.status_code == 403

    async def test_author_can_dismiss_challenge(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("The beat stands."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        beat_id = beats[0].id

        await _challenge_beat(client, game_id, act_id, scene_id, beat_id, challenger_user_id=2)

        await _login(client, 1)
        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/challenge/dismiss",
            follow_redirects=False,
        )
        assert r.status_code == 303

        beats = await _get_beats(scene_id, db)
        assert beats[0].status == BeatStatus.canon
        assert beats[0].challenge_outcome == "dismissed"
        # challenge_reason and challenged_by_id are preserved for history display
        assert beats[0].challenge_reason is not None
        assert beats[0].challenged_by_id is not None

    async def test_non_author_cannot_dismiss(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Something."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        beat_id = beats[0].id

        await _challenge_beat(client, game_id, act_id, scene_id, beat_id, challenger_user_id=2)

        # Challenger tries to dismiss (should fail)
        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/challenge/dismiss",
            follow_redirects=False,
        )
        assert r.status_code == 403

    async def test_dismiss_notifies_challenger(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("The beat stands."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        beat_id = beats[0].id

        await _challenge_beat(client, game_id, act_id, scene_id, beat_id, challenger_user_id=2)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/challenge/dismiss",
            follow_redirects=False,
        )

        notifications = await _get_notifications(2, db)
        assert any(
            n.notification_type == NotificationType.challenge_dismissed for n in notifications
        )

    async def test_any_member_can_comment(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Something happens."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        beat_id = beats[0].id

        await _challenge_beat(client, game_id, act_id, scene_id, beat_id, challenger_user_id=2)

        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/comments",
            data={"content": "I think this is fine actually."},
            follow_redirects=False,
        )
        assert r.status_code == 303

        comments = await _get_beat_comments(beat_id, db)
        assert len(comments) == 1
        assert comments[0].content == "I think this is fine actually."

    async def test_non_member_cannot_comment(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Something."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        beat_id = beats[0].id

        await _challenge_beat(client, game_id, act_id, scene_id, beat_id, challenger_user_id=2)

        await _login(client, 3)
        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/comments",
            data={"content": "I'm not in this game."},
            follow_redirects=False,
        )
        assert r.status_code == 403

    async def test_comment_on_non_challenged_beat_rejected(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("A canon beat."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        beat_id = beats[0].id
        assert beats[0].status == BeatStatus.canon

        await _login(client, 2)
        r = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/comments",
            data={"content": "Just commenting."},
            follow_redirects=False,
        )
        assert r.status_code == 400

    async def test_comment_notifies_beat_author(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db, extra_members=[2])
        act_id = await _create_active_act(game_id, db)
        scene_id = await _create_active_scene(act_id, game_id, db)

        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("A beat by user 1."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id, db)
        beat_id = beats[0].id

        await _challenge_beat(client, game_id, act_id, scene_id, beat_id, challenger_user_id=2)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats/{beat_id}/comments",
            data={"content": "Here's my suggestion."},
            follow_redirects=False,
        )

        notifications = await _get_notifications(1, db)
        assert any(
            n.notification_type == NotificationType.beat_comment_added for n in notifications
        )
