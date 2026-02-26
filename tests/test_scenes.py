"""Tests for scene creation and voting routes."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from loom.database import Base, get_db
from loom.main import _DEV_USERS, app
from loom.models import (
    Act,
    ActStatus,
    Beat,
    BeatStatus,
    Character,
    EventType,
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
    """Create a game, add optional extra members, activate it."""
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

    if not extra_members:
        await client.post(f"/games/{game_id}/session0/propose-ready", follow_redirects=False)
    else:
        async with _test_session_factory() as db:
            result = await db.execute(select(Game).where(Game.id == game_id))
            game = result.scalar_one()
            game.status = GameStatus.active
            await db.commit()

    return game_id


async def _create_active_act(game_id: int) -> int:
    """Insert an active act directly and return its id."""
    async with _test_session_factory() as db:
        act = Act(
            game_id=game_id,
            guiding_question="What is at stake?",
            status=ActStatus.active,
            order=1,
        )
        db.add(act)
        await db.commit()
        return act.id


async def _create_character(game_id: int, owner_id: int, name: str = "Hero") -> int:
    """Insert a character and return its id."""
    async with _test_session_factory() as db:
        char = Character(game_id=game_id, owner_id=owner_id, name=name)
        db.add(char)
        await db.commit()
        return char.id


async def _get_scenes(act_id: int) -> list[Scene]:
    async with _test_session_factory() as db:
        result = await db.execute(select(Scene).where(Scene.act_id == act_id).order_by(Scene.order))
        return list(result.scalars().all())


async def _get_scene_character_ids(scene_id: int) -> list[int]:
    async with _test_session_factory() as db:
        result = await db.execute(
            select(Scene)
            .where(Scene.id == scene_id)
            .options(selectinload(Scene.characters_present))
        )
        scene = result.scalar_one()
        return [c.id for c in scene.characters_present]


async def _get_proposals(game_id: int) -> list[VoteProposal]:
    async with _test_session_factory() as db:
        result = await db.execute(select(VoteProposal).where(VoteProposal.game_id == game_id))
        return list(result.scalars().all())


async def _get_votes(proposal_id: int) -> list[Vote]:
    async with _test_session_factory() as db:
        result = await db.execute(select(Vote).where(Vote.proposal_id == proposal_id))
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Scenes view
# ---------------------------------------------------------------------------


class TestScenesView:
    async def test_view_requires_membership(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        await _login(client, 2)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_view_accessible_to_member(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False
        )
        assert response.status_code == 200

    async def test_view_404_for_unknown_act(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        response = await client.get(f"/games/{game_id}/acts/9999/scenes", follow_redirects=False)
        assert response.status_code == 404

    async def test_view_403_for_non_active_act(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        async with _test_session_factory() as db:
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

    async def test_view_shows_no_scenes_message(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False
        )
        assert b"No scenes yet" in response.content

    async def test_view_shows_propose_form_when_active(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes", follow_redirects=False
        )
        assert b"Propose a New Scene" in response.content

    async def test_view_hides_form_when_proposal_pending(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

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
    async def test_creates_scene_in_active_status(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id)
        assert len(scenes) == 1
        assert scenes[0].status == SceneStatus.active
        assert scenes[0].guiding_question == "Will they escape?"

    async def test_scene_location_optional(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id)
        assert scenes[0].location is None

    async def test_scene_location_stored(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={
                "guiding_question": "Will they escape?",
                "location": "The Vault",
                "character_ids": str(char_id),
            },
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id)
        assert scenes[0].location == "The Vault"

    async def test_scene_tension_stored(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={
                "guiding_question": "Will they escape?",
                "tension": "7",
                "character_ids": str(char_id),
            },
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id)
        assert scenes[0].tension == 7

    async def test_tension_defaults_to_5(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id)
        assert scenes[0].tension == 5

    async def test_characters_present_stored(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id)
        char_ids = await _get_scene_character_ids(scenes[0].id)
        assert char_id in char_ids

    async def test_proposal_auto_approved(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id)
        scene_proposals = [p for p in proposals if p.proposal_type == ProposalType.scene_proposal]
        assert len(scene_proposals) == 1
        assert scene_proposals[0].status == ProposalStatus.approved

    async def test_implicit_yes_vote_recorded(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id)
        scene_proposals = [p for p in proposals if p.proposal_type == ProposalType.scene_proposal]
        votes = await _get_votes(scene_proposals[0].id)
        assert len(votes) == 1
        assert votes[0].choice == VoteChoice.yes

    async def test_redirects_to_scenes_page(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == f"/games/{game_id}/acts/{act_id}/scenes"

    async def test_scene_order_increments(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

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
        scenes = await _get_scenes(act_id)
        assert scenes[0].order == 1
        assert scenes[1].order == 2

    async def test_active_scene_completed_when_new_approved(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

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
        scenes = await _get_scenes(act_id)
        assert scenes[0].status == SceneStatus.complete
        assert scenes[1].status == SceneStatus.active


# ---------------------------------------------------------------------------
# Propose scene — multi-player (vote required)
# ---------------------------------------------------------------------------


class TestProposeSceneMultiPlayer:
    async def test_scene_starts_proposed(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Who controls the vault?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        scenes = await _get_scenes(act_id)
        assert scenes[0].status == SceneStatus.proposed

    async def test_proposal_remains_open(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Who controls the vault?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id)
        scene_proposals = [p for p in proposals if p.proposal_type == ProposalType.scene_proposal]
        assert scene_proposals[0].status == ProposalStatus.open

    async def test_second_yes_vote_activates_scene(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Who controls the vault?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id)
        scene_proposals = [p for p in proposals if p.proposal_type == ProposalType.scene_proposal]
        proposal_id = scene_proposals[0].id

        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal_id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )

        scenes = await _get_scenes(act_id)
        assert scenes[0].status == SceneStatus.active

    async def test_vote_redirects_to_scenes_page(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Who controls the vault?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        proposals = await _get_proposals(game_id)
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
    async def test_requires_active_game(self, client: AsyncClient) -> None:
        await _login(client, 1)
        r = await client.post("/games", data={"name": "G", "pitch": "P"}, follow_redirects=False)
        game_id = int(r.headers["location"].rsplit("/", 1)[-1])
        # Insert an act directly to bypass game status check on act lookup
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)
        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Does this work?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_requires_active_act(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        async with _test_session_factory() as db:
            act = Act(
                game_id=game_id,
                guiding_question="Proposed act?",
                status=ActStatus.proposed,
                order=1,
            )
            db.add(act)
            await db.commit()
            act_id = act.id
        char_id = await _create_character(game_id, 1)
        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will this work?", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_requires_membership(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Am I allowed?", "character_ids": "1"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_requires_guiding_question(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)
        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "   ", "character_ids": str(char_id)},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_requires_at_least_one_character(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?"},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_rejects_character_from_another_game(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)

        # Create a second game and a character in it
        r2 = await client.post(
            "/games", data={"name": "Other Game", "pitch": "P"}, follow_redirects=False
        )
        other_game_id = int(r2.headers["location"].rsplit("/", 1)[-1])
        other_char_id = await _create_character(other_game_id, 1)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes",
            data={"guiding_question": "Will they escape?", "character_ids": str(other_char_id)},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_rejects_invalid_tension_low(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)
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

    async def test_rejects_invalid_tension_high(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)
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

    async def test_rejects_duplicate_open_proposal(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client, extra_members=[2])
        await _login(client, 1)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

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


async def _create_active_scene(act_id: int, game_id: int) -> int:
    """Insert an active scene with a character and return its id."""
    async with _test_session_factory() as db:
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
    async def test_accessible_to_member(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", follow_redirects=False
        )
        assert response.status_code == 200

    async def test_requires_membership(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)
        await _login(client, 2)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_404_for_unknown_scene(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/9999", follow_redirects=False
        )
        assert response.status_code == 404

    async def test_shows_scene_info(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", follow_redirects=False
        )
        assert b"What is at stake?" in response.content
        assert b"Tension" in response.content

    async def test_shows_empty_beat_timeline(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", follow_redirects=False
        )
        assert b"No beats yet" in response.content

    async def test_shows_filter_controls(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", follow_redirects=False
        )
        assert b"IC Only" in response.content
        assert b"OOC Only" in response.content

    async def test_htmx_polling_attr_present(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", follow_redirects=False
        )
        assert b"hx-trigger" in response.content
        assert b"every 5s" in response.content

    async def test_filter_query_param_accepted(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)
        for f in ("all", "ic", "ooc"):
            response = await client.get(
                f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}?filter={f}",
                follow_redirects=False,
            )
            assert response.status_code == 200

    async def test_default_tension_uses_last_scene_tension(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        char_id = await _create_character(game_id, 1)

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
    async def test_returns_200_for_member(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats", follow_redirects=False
        )
        assert response.status_code == 200

    async def test_requires_membership(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)
        await _login(client, 2)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats", follow_redirects=False
        )
        assert response.status_code == 403

    async def test_404_for_unknown_scene(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/9999/beats", follow_redirects=False
        )
        assert response.status_code == 404

    async def test_shows_empty_message(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)
        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats", follow_redirects=False
        )
        assert b"No beats yet" in response.content

    async def test_filter_param_accepted(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)
        for f in ("all", "ic", "ooc"):
            response = await client.get(
                f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats?filter={f}",
                follow_redirects=False,
            )
            assert response.status_code == 200


# ---------------------------------------------------------------------------
# Beat submission
# ---------------------------------------------------------------------------


async def _get_beats(scene_id: int) -> list[Beat]:
    async with _test_session_factory() as db:
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


class TestSubmitBeat:
    async def test_creates_beat_with_narrative_event(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("The hero steps forward."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id)
        assert len(beats) == 1
        assert len(beats[0].events) == 1
        assert beats[0].events[0].content == "The hero steps forward."

    async def test_beat_is_immediately_canon(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Action."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id)
        assert beats[0].status == BeatStatus.canon

    async def test_event_type_is_narrative(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Action."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id)
        assert beats[0].events[0].type == EventType.narrative

    async def test_beat_order_increments(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

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
        beats = await _get_beats(scene_id)
        assert beats[0].order == 1
        assert beats[1].order == 2

    async def test_redirects_to_scene_detail(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Action."),
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == (f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}")

    async def test_requires_membership(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)
        await _login(client, 2)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Sneaky."),
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_rejects_empty_content(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("   "),
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_rejects_beat_on_inactive_scene(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        async with _test_session_factory() as db:
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

    async def test_beat_appears_in_timeline(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

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

    async def test_form_shown_for_active_scene(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}",
            follow_redirects=False,
        )
        assert b"Submit Beat" in response.content

    async def test_rejects_no_events(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_rejects_invalid_event_type(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={"event_type": "oracle", "event_content": "Something"},
            follow_redirects=False,
        )
        assert response.status_code == 422


class TestSubmitBeatMultiEvent:
    async def test_ooc_event_stored(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={"event_type": "ooc", "event_content": "Does this trigger a safety tool?"},
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id)
        assert len(beats) == 1
        assert beats[0].events[0].type == EventType.ooc
        assert beats[0].events[0].content == "Does this trigger a safety tool?"

    async def test_roll_event_stored(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={
                "event_type": "roll",
                "event_notation": "2d6+3",
                "event_reason": "Climbing the wall",
            },
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id)
        assert len(beats) == 1
        ev = beats[0].events[0]
        assert ev.type == EventType.roll
        assert ev.roll_notation == "2d6+3"
        assert ev.content == "Climbing the wall"
        # 2d6+3: min=5, max=15
        assert ev.roll_result is not None
        assert 5 <= ev.roll_result <= 15

    async def test_roll_without_reason(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={"event_type": "roll", "event_notation": "1d20"},
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id)
        ev = beats[0].events[0]
        assert ev.roll_notation == "1d20"
        assert ev.content is None
        assert ev.roll_result is not None
        assert 1 <= ev.roll_result <= 20

    async def test_roll_invalid_notation_rejected(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={"event_type": "roll", "event_notation": "roll some dice"},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_roll_requires_notation(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={"event_type": "roll", "event_notation": ""},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_multi_event_beat_stored_in_order(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

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
        beats = await _get_beats(scene_id)
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

    async def test_multi_event_all_appear_in_timeline(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

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
    async def test_minor_beat_is_immediately_canon(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={
                "event_type": "narrative",
                "event_content": "A minor thing happens.",
                "beat_significance": "minor",
            },
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id)
        assert beats[0].significance.value == "minor"
        assert beats[0].status == BeatStatus.canon

    async def test_major_beat_enters_proposed_status(self, client: AsyncClient) -> None:
        # Needs 2 players: proposer's implicit yes (1/2) does not meet threshold (>1).
        game_id = await _create_active_game(client, extra_members=[2])
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={
                "event_type": "narrative",
                "event_content": "A major revelation.",
                "beat_significance": "major",
            },
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id)
        assert beats[0].significance.value == "major"
        assert beats[0].status == BeatStatus.proposed

    async def test_major_beat_single_player_auto_approves(self, client: AsyncClient) -> None:
        # Single-player: proposer's implicit yes (1/1) exceeds threshold (>0.5) → auto-canon.
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={
                "event_type": "narrative",
                "event_content": "A solo revelation.",
                "beat_significance": "major",
            },
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id)
        assert beats[0].significance.value == "major"
        assert beats[0].status == BeatStatus.canon

    async def test_default_significance_is_minor(self, client: AsyncClient) -> None:
        """No beat_significance field defaults to minor (AI stub always returns minor)."""
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data=_narrative_data("Something happens."),
            follow_redirects=False,
        )
        beats = await _get_beats(scene_id)
        assert beats[0].significance.value == "minor"
        assert beats[0].status == BeatStatus.canon

    async def test_invalid_significance_rejected(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        response = await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
            data={"event_type": "narrative", "event_content": "Text.", "beat_significance": "huge"},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_form_shows_significance_selector(self, client: AsyncClient) -> None:
        game_id = await _create_active_game(client)
        act_id = await _create_active_act(game_id)
        scene_id = await _create_active_scene(act_id, game_id)

        response = await client.get(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}",
            follow_redirects=False,
        )
        assert b"beat_significance" in response.content
        assert b"Minor" in response.content
        assert b"Major" in response.content
        assert b"AI suggests" in response.content
