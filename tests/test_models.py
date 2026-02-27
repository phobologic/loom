"""ORM-level integration tests for Loom data models."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from loom import models as _models  # noqa: F401 - registers models with Base.metadata
from loom.models import (
    Act,
    ActStatus,
    Beat,
    BeatSignificance,
    BeatStatus,
    Character,
    Event,
    EventType,
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    Scene,
    SceneStatus,
    User,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(session: AsyncSession, display_name: str = "Alice") -> User:
    user = User(display_name=display_name)
    session.add(user)
    await session.flush()
    return user


async def _make_game(session: AsyncSession, name: str = "Test Game") -> Game:
    game = Game(name=name)
    session.add(game)
    await session.flush()
    return game


async def _make_act(session: AsyncSession, game: Game) -> Act:
    act = Act(game_id=game.id, guiding_question="What lurks in the dark?")
    session.add(act)
    await session.flush()
    return act


async def _make_scene(session: AsyncSession, act: Act) -> Scene:
    scene = Scene(act_id=act.id, guiding_question="Can they survive the night?")
    session.add(scene)
    await session.flush()
    return scene


async def _make_beat(session: AsyncSession, scene: Scene, author: User | None = None) -> Beat:
    beat = Beat(scene_id=scene.id, author_id=author.id if author else None)
    session.add(beat)
    await session.flush()
    return beat


# ---------------------------------------------------------------------------
# TestUserModel
# ---------------------------------------------------------------------------


class TestUserModel:
    async def test_create_user(self, db: AsyncSession):
        user = await _make_user(db)
        assert user.id is not None
        assert user.display_name == "Alice"
        assert user.email is None
        assert user.oauth_provider is None

    async def test_user_has_timestamps(self, db: AsyncSession):
        user = await _make_user(db)
        assert user.created_at is not None
        assert user.updated_at is not None


# ---------------------------------------------------------------------------
# TestGameModel
# ---------------------------------------------------------------------------


class TestGameModel:
    async def test_create_game(self, db: AsyncSession):
        game = await _make_game(db)
        assert game.id is not None
        assert game.name == "Test Game"
        assert game.status == GameStatus.setup
        assert game.pitch is None
        assert game.invite_token is None

    async def test_game_cascade_deletes_members(self, db: AsyncSession):
        user = await _make_user(db)
        game = await _make_game(db)
        member = GameMember(game_id=game.id, user_id=user.id, role=MemberRole.organizer)
        db.add(member)
        await db.flush()
        member_id = member.id

        await db.delete(game)
        await db.flush()

        result = await db.get(GameMember, member_id)
        assert result is None


# ---------------------------------------------------------------------------
# TestActModel
# ---------------------------------------------------------------------------


class TestActModel:
    async def test_create_act(self, db: AsyncSession):
        game = await _make_game(db)
        act = await _make_act(db, game)
        assert act.id is not None
        assert act.status == ActStatus.proposed
        assert act.order == 0

    async def test_act_cascade_from_game(self, db: AsyncSession):
        game = await _make_game(db)
        act = await _make_act(db, game)
        act_id = act.id

        await db.delete(game)
        await db.flush()

        result = await db.get(Act, act_id)
        assert result is None


# ---------------------------------------------------------------------------
# TestSceneModel
# ---------------------------------------------------------------------------


class TestSceneModel:
    async def test_create_scene_defaults(self, db: AsyncSession):
        game = await _make_game(db)
        act = await _make_act(db, game)
        scene = await _make_scene(db, act)
        assert scene.tension == 5
        assert scene.status == SceneStatus.proposed

    async def test_scene_tension_constraint(self, db: AsyncSession):
        game = await _make_game(db)
        act = await _make_act(db, game)
        bad_scene = Scene(act_id=act.id, guiding_question="Q", tension=10)
        db.add(bad_scene)
        with pytest.raises(IntegrityError):
            await db.flush()

    async def test_scene_cascade_from_act(self, db: AsyncSession):
        game = await _make_game(db)
        act = await _make_act(db, game)
        scene = await _make_scene(db, act)
        scene_id = scene.id

        await db.delete(act)
        await db.flush()

        result = await db.get(Scene, scene_id)
        assert result is None


# ---------------------------------------------------------------------------
# TestBeatModel
# ---------------------------------------------------------------------------


class TestBeatModel:
    async def test_create_beat_defaults(self, db: AsyncSession):
        game = await _make_game(db)
        act = await _make_act(db, game)
        scene = await _make_scene(db, act)
        beat = await _make_beat(db, scene)
        assert beat.significance == BeatSignificance.minor
        assert beat.status == BeatStatus.proposed
        assert beat.order == 0

    async def test_beat_cascade_from_scene(self, db: AsyncSession):
        game = await _make_game(db)
        act = await _make_act(db, game)
        scene = await _make_scene(db, act)
        beat = await _make_beat(db, scene)
        beat_id = beat.id

        await db.delete(scene)
        await db.flush()

        result = await db.get(Beat, beat_id)
        assert result is None

    async def test_beat_author_set_null_on_user_delete(self, db: AsyncSession):
        user = await _make_user(db)
        game = await _make_game(db)
        act = await _make_act(db, game)
        scene = await _make_scene(db, act)
        beat = await _make_beat(db, scene, author=user)
        beat_id = beat.id
        assert beat.author_id == user.id

        await db.delete(user)
        await db.flush()
        db.expire_all()

        refreshed = await db.get(Beat, beat_id)
        assert refreshed is not None
        assert refreshed.author_id is None


# ---------------------------------------------------------------------------
# TestEventModel
# ---------------------------------------------------------------------------


class TestEventModel:
    async def _setup(self, session: AsyncSession) -> Beat:
        game = await _make_game(session)
        act = await _make_act(session, game)
        scene = await _make_scene(session, act)
        return await _make_beat(session, scene)

    async def test_narrative_event(self, db: AsyncSession):
        beat = await self._setup(db)
        event = Event(
            beat_id=beat.id, type=EventType.narrative, content="The hero enters.", order=0
        )
        db.add(event)
        await db.flush()
        assert event.id is not None
        assert event.type == EventType.narrative

    async def test_roll_event(self, db: AsyncSession):
        beat = await self._setup(db)
        event = Event(
            beat_id=beat.id,
            type=EventType.roll,
            roll_notation="2d6+1",
            roll_result=9,
            order=0,
        )
        db.add(event)
        await db.flush()
        assert event.roll_notation == "2d6+1"
        assert event.roll_result == 9

    async def test_oracle_event_interpretations_property(self, db: AsyncSession):
        beat = await self._setup(db)
        event = Event(
            beat_id=beat.id, type=EventType.oracle, oracle_query="Will they survive?", order=0
        )
        event.interpretations = ["Yes, barely.", "No, but..."]
        db.add(event)
        await db.flush()
        assert event.interpretations == ["Yes, barely.", "No, but..."]

    async def test_fortune_roll_event(self, db: AsyncSession):
        beat = await self._setup(db)
        event = Event(
            beat_id=beat.id,
            type=EventType.fortune_roll,
            fortune_roll_odds="likely",
            fortune_roll_result="yes",
            fortune_roll_tension=6,
            word_seed_action="strike",
            word_seed_descriptor="sudden",
            order=0,
        )
        db.add(event)
        await db.flush()
        assert event.fortune_roll_odds == "likely"
        assert event.word_seed_action == "strike"

    async def test_events_cascade_from_beat(self, db: AsyncSession):
        beat = await self._setup(db)
        event = Event(beat_id=beat.id, type=EventType.narrative, content="Text", order=0)
        db.add(event)
        await db.flush()
        event_id = event.id

        await db.delete(beat)
        await db.flush()

        result = await db.get(Event, event_id)
        assert result is None


# ---------------------------------------------------------------------------
# TestCharacterModel
# ---------------------------------------------------------------------------


class TestCharacterModel:
    async def test_create_character(self, db: AsyncSession):
        user = await _make_user(db)
        game = await _make_game(db)
        char = Character(game_id=game.id, owner_id=user.id, name="Sir Reginald")
        db.add(char)
        await db.flush()
        assert char.id is not None
        assert char.name == "Sir Reginald"

    async def test_character_owner_set_null_on_user_delete(self, db: AsyncSession):
        user = await _make_user(db)
        game = await _make_game(db)
        char = Character(game_id=game.id, owner_id=user.id, name="Sir Reginald")
        db.add(char)
        await db.flush()
        char_id = char.id

        await db.delete(user)
        await db.flush()
        db.expire_all()

        refreshed = await db.get(Character, char_id)
        assert refreshed is not None
        assert refreshed.owner_id is None

    async def test_character_in_scene(self, db: AsyncSession):
        user = await _make_user(db)
        game = await _make_game(db)
        act = await _make_act(db, game)
        scene = await _make_scene(db, act)
        char = Character(game_id=game.id, owner_id=user.id, name="Hero")
        db.add(char)
        await db.flush()

        # Must load the collection explicitly before mutating (async SQLAlchemy has no lazy loading)
        await db.refresh(scene, ["characters_present"])
        scene.characters_present.append(char)
        await db.flush()

        await db.refresh(scene, ["characters_present"])
        assert char in scene.characters_present


# ---------------------------------------------------------------------------
# TestFullGameFlow
# ---------------------------------------------------------------------------


class TestFullGameFlow:
    async def test_full_flow_and_cascade(self, db: AsyncSession):
        # Build the full hierarchy
        user = await _make_user(db)
        game = await _make_game(db)
        member = GameMember(game_id=game.id, user_id=user.id, role=MemberRole.organizer)
        db.add(member)
        act = await _make_act(db, game)
        scene = await _make_scene(db, act)
        beat = await _make_beat(db, scene, author=user)
        event = Event(beat_id=beat.id, type=EventType.narrative, content="Prologue.", order=0)
        db.add(event)
        await db.flush()

        event_id = event.id
        beat_id = beat.id
        scene_id = scene.id
        act_id = act.id

        # Deleting game should cascade to everything
        await db.delete(game)
        await db.flush()

        assert await db.get(Act, act_id) is None
        assert await db.get(Scene, scene_id) is None
        assert await db.get(Beat, beat_id) is None
        assert await db.get(Event, event_id) is None
