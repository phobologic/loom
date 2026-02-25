"""ORM-level integration tests for Loom data models."""

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from loom import models as _models  # noqa: F401 - registers models with Base.metadata
from loom.database import Base
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

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    """Async session backed by an in-memory SQLite database."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


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
    async def test_create_user(self, db_session: AsyncSession):
        user = await _make_user(db_session)
        assert user.id is not None
        assert user.display_name == "Alice"
        assert user.email is None
        assert user.oauth_provider is None

    async def test_user_has_timestamps(self, db_session: AsyncSession):
        user = await _make_user(db_session)
        assert user.created_at is not None
        assert user.updated_at is not None


# ---------------------------------------------------------------------------
# TestGameModel
# ---------------------------------------------------------------------------


class TestGameModel:
    async def test_create_game(self, db_session: AsyncSession):
        game = await _make_game(db_session)
        assert game.id is not None
        assert game.name == "Test Game"
        assert game.status == GameStatus.setup
        assert game.pitch is None
        assert game.invite_token is None

    async def test_game_cascade_deletes_members(self, db_session: AsyncSession):
        user = await _make_user(db_session)
        game = await _make_game(db_session)
        member = GameMember(game_id=game.id, user_id=user.id, role=MemberRole.organizer)
        db_session.add(member)
        await db_session.flush()
        member_id = member.id

        await db_session.delete(game)
        await db_session.flush()

        result = await db_session.get(GameMember, member_id)
        assert result is None


# ---------------------------------------------------------------------------
# TestActModel
# ---------------------------------------------------------------------------


class TestActModel:
    async def test_create_act(self, db_session: AsyncSession):
        game = await _make_game(db_session)
        act = await _make_act(db_session, game)
        assert act.id is not None
        assert act.status == ActStatus.proposed
        assert act.order == 0

    async def test_act_cascade_from_game(self, db_session: AsyncSession):
        game = await _make_game(db_session)
        act = await _make_act(db_session, game)
        act_id = act.id

        await db_session.delete(game)
        await db_session.flush()

        result = await db_session.get(Act, act_id)
        assert result is None


# ---------------------------------------------------------------------------
# TestSceneModel
# ---------------------------------------------------------------------------


class TestSceneModel:
    async def test_create_scene_defaults(self, db_session: AsyncSession):
        game = await _make_game(db_session)
        act = await _make_act(db_session, game)
        scene = await _make_scene(db_session, act)
        assert scene.tension == 5
        assert scene.status == SceneStatus.proposed

    async def test_scene_tension_constraint(self, db_session: AsyncSession):
        game = await _make_game(db_session)
        act = await _make_act(db_session, game)
        bad_scene = Scene(act_id=act.id, guiding_question="Q", tension=10)
        db_session.add(bad_scene)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_scene_cascade_from_act(self, db_session: AsyncSession):
        game = await _make_game(db_session)
        act = await _make_act(db_session, game)
        scene = await _make_scene(db_session, act)
        scene_id = scene.id

        await db_session.delete(act)
        await db_session.flush()

        result = await db_session.get(Scene, scene_id)
        assert result is None


# ---------------------------------------------------------------------------
# TestBeatModel
# ---------------------------------------------------------------------------


class TestBeatModel:
    async def test_create_beat_defaults(self, db_session: AsyncSession):
        game = await _make_game(db_session)
        act = await _make_act(db_session, game)
        scene = await _make_scene(db_session, act)
        beat = await _make_beat(db_session, scene)
        assert beat.significance == BeatSignificance.minor
        assert beat.status == BeatStatus.proposed
        assert beat.order == 0

    async def test_beat_cascade_from_scene(self, db_session: AsyncSession):
        game = await _make_game(db_session)
        act = await _make_act(db_session, game)
        scene = await _make_scene(db_session, act)
        beat = await _make_beat(db_session, scene)
        beat_id = beat.id

        await db_session.delete(scene)
        await db_session.flush()

        result = await db_session.get(Beat, beat_id)
        assert result is None

    async def test_beat_author_set_null_on_user_delete(self, db_session: AsyncSession):
        user = await _make_user(db_session)
        game = await _make_game(db_session)
        act = await _make_act(db_session, game)
        scene = await _make_scene(db_session, act)
        beat = await _make_beat(db_session, scene, author=user)
        beat_id = beat.id
        assert beat.author_id == user.id

        await db_session.delete(user)
        await db_session.flush()
        db_session.expire_all()

        refreshed = await db_session.get(Beat, beat_id)
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

    async def test_narrative_event(self, db_session: AsyncSession):
        beat = await self._setup(db_session)
        event = Event(
            beat_id=beat.id, type=EventType.narrative, content="The hero enters.", order=0
        )
        db_session.add(event)
        await db_session.flush()
        assert event.id is not None
        assert event.type == EventType.narrative

    async def test_roll_event(self, db_session: AsyncSession):
        beat = await self._setup(db_session)
        event = Event(
            beat_id=beat.id,
            type=EventType.roll,
            roll_notation="2d6+1",
            roll_result=9,
            order=0,
        )
        db_session.add(event)
        await db_session.flush()
        assert event.roll_notation == "2d6+1"
        assert event.roll_result == 9

    async def test_oracle_event_interpretations_property(self, db_session: AsyncSession):
        beat = await self._setup(db_session)
        event = Event(
            beat_id=beat.id, type=EventType.oracle, oracle_query="Will they survive?", order=0
        )
        event.interpretations = ["Yes, barely.", "No, but..."]
        db_session.add(event)
        await db_session.flush()
        assert event.interpretations == ["Yes, barely.", "No, but..."]

    async def test_fortune_roll_event(self, db_session: AsyncSession):
        beat = await self._setup(db_session)
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
        db_session.add(event)
        await db_session.flush()
        assert event.fortune_roll_odds == "likely"
        assert event.word_seed_action == "strike"

    async def test_events_cascade_from_beat(self, db_session: AsyncSession):
        beat = await self._setup(db_session)
        event = Event(beat_id=beat.id, type=EventType.narrative, content="Text", order=0)
        db_session.add(event)
        await db_session.flush()
        event_id = event.id

        await db_session.delete(beat)
        await db_session.flush()

        result = await db_session.get(Event, event_id)
        assert result is None


# ---------------------------------------------------------------------------
# TestCharacterModel
# ---------------------------------------------------------------------------


class TestCharacterModel:
    async def test_create_character(self, db_session: AsyncSession):
        user = await _make_user(db_session)
        game = await _make_game(db_session)
        char = Character(game_id=game.id, owner_id=user.id, name="Sir Reginald")
        db_session.add(char)
        await db_session.flush()
        assert char.id is not None
        assert char.name == "Sir Reginald"

    async def test_character_owner_set_null_on_user_delete(self, db_session: AsyncSession):
        user = await _make_user(db_session)
        game = await _make_game(db_session)
        char = Character(game_id=game.id, owner_id=user.id, name="Sir Reginald")
        db_session.add(char)
        await db_session.flush()
        char_id = char.id

        await db_session.delete(user)
        await db_session.flush()
        db_session.expire_all()

        refreshed = await db_session.get(Character, char_id)
        assert refreshed is not None
        assert refreshed.owner_id is None

    async def test_character_in_scene(self, db_session: AsyncSession):
        user = await _make_user(db_session)
        game = await _make_game(db_session)
        act = await _make_act(db_session, game)
        scene = await _make_scene(db_session, act)
        char = Character(game_id=game.id, owner_id=user.id, name="Hero")
        db_session.add(char)
        await db_session.flush()

        # Must load the collection explicitly before mutating (async SQLAlchemy has no lazy loading)
        await db_session.refresh(scene, ["characters_present"])
        scene.characters_present.append(char)
        await db_session.flush()

        await db_session.refresh(scene, ["characters_present"])
        assert char in scene.characters_present


# ---------------------------------------------------------------------------
# TestFullGameFlow
# ---------------------------------------------------------------------------


class TestFullGameFlow:
    async def test_full_flow_and_cascade(self, db_session: AsyncSession):
        # Build the full hierarchy
        user = await _make_user(db_session)
        game = await _make_game(db_session)
        member = GameMember(game_id=game.id, user_id=user.id, role=MemberRole.organizer)
        db_session.add(member)
        act = await _make_act(db_session, game)
        scene = await _make_scene(db_session, act)
        beat = await _make_beat(db_session, scene, author=user)
        event = Event(beat_id=beat.id, type=EventType.narrative, content="Prologue.", order=0)
        db_session.add(event)
        await db_session.flush()

        event_id = event.id
        beat_id = beat.id
        scene_id = scene.id
        act_id = act.id

        # Deleting game should cascade to everything
        await db_session.delete(game)
        await db_session.flush()

        assert await db_session.get(Act, act_id) is None
        assert await db_session.get(Scene, scene_id) is None
        assert await db_session.get(Beat, beat_id) is None
        assert await db_session.get(Event, event_id) is None
