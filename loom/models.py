"""SQLAlchemy ORM models for the Loom play loop."""

from __future__ import annotations

import enum
import json
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from loom.database import Base

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class GameStatus(str, enum.Enum):
    """Lifecycle status of a game."""

    setup = "setup"
    active = "active"
    paused = "paused"
    archived = "archived"


class MemberRole(str, enum.Enum):
    """Role of a user within a game."""

    organizer = "organizer"
    player = "player"


class ActStatus(str, enum.Enum):
    """Lifecycle status of an act."""

    proposed = "proposed"
    active = "active"
    complete = "complete"


class SceneStatus(str, enum.Enum):
    """Lifecycle status of a scene."""

    proposed = "proposed"
    active = "active"
    complete = "complete"


class BeatSignificance(str, enum.Enum):
    """Narrative weight of a beat."""

    major = "major"
    minor = "minor"


class BeatStatus(str, enum.Enum):
    """Approval status of a beat."""

    proposed = "proposed"
    approved = "approved"
    canon = "canon"
    challenged = "challenged"
    revised = "revised"
    rejected = "rejected"


class EventType(str, enum.Enum):
    """Type of event within a beat."""

    narrative = "narrative"
    roll = "roll"
    oracle = "oracle"
    fortune_roll = "fortune_roll"
    ooc = "ooc"


class TieBreakingMethod(str, enum.Enum):
    """How tied votes on a major beat are resolved."""

    random = "random"
    proposer = "proposer"
    challenger = "challenger"


class BeatSignificanceThreshold(str, enum.Enum):
    """How aggressively the system flags beats as major."""

    flag_most = "flag_most"
    flag_obvious = "flag_obvious"
    minimal = "minimal"


class PromptStatus(str, enum.Enum):
    """Lifecycle status of a Session 0 prompt."""

    pending = "pending"  # not yet reached
    active = "active"  # collecting contributions now
    skipped = "skipped"  # organizer skipped
    complete = "complete"  # synthesis accepted


class SafetyToolKind(str, enum.Enum):
    """Whether a safety tool is a hard limit or a fade-to-black."""

    line = "line"
    veil = "veil"


# ---------------------------------------------------------------------------
# Timestamp mixin
# ---------------------------------------------------------------------------


class TimestampMixin:
    """Adds created_at and updated_at columns to any model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Association table (must be defined before Scene and Character)
# ---------------------------------------------------------------------------

scene_characters = sa.Table(
    "scene_characters",
    Base.metadata,
    sa.Column(
        "scene_id",
        ForeignKey("scenes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column(
        "character_id",
        ForeignKey("characters.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class User(TimestampMixin, Base):
    """A Loom user account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    oauth_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)

    memberships: Mapped[list[GameMember]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    characters: Mapped[list[Character]] = relationship(
        back_populates="owner",
        foreign_keys="Character.owner_id",
    )
    beats: Mapped[list[Beat]] = relationship(back_populates="author")


class Game(TimestampMixin, Base):
    """A single Loom game instance."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    pitch: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[GameStatus] = mapped_column(
        Enum(GameStatus, native_enum=False), nullable=False, default=GameStatus.setup
    )
    invite_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    # Configurable settings
    silence_timer_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    tie_breaking_method: Mapped[TieBreakingMethod] = mapped_column(
        Enum(TieBreakingMethod, native_enum=False),
        nullable=False,
        default=TieBreakingMethod.random,
    )
    beat_significance_threshold: Mapped[BeatSignificanceThreshold] = mapped_column(
        Enum(BeatSignificanceThreshold, native_enum=False),
        nullable=False,
        default=BeatSignificanceThreshold.flag_obvious,
    )
    max_consecutive_beats: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    auto_generate_narrative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fortune_roll_contest_window_hours: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )
    starting_tension: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    members: Mapped[list[GameMember]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    invitations: Mapped[list[Invitation]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    acts: Mapped[list[Act]] = relationship(back_populates="game", cascade="all, delete-orphan")
    characters: Mapped[list[Character]] = relationship(
        back_populates="game",
        foreign_keys="Character.game_id",
        cascade="all, delete-orphan",
    )
    session0_prompts: Mapped[list[Session0Prompt]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="Session0Prompt.order",
    )
    safety_tools: Mapped[list[GameSafetyTool]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="GameSafetyTool.created_at",
    )


class GameMember(TimestampMixin, Base):
    """Membership record linking a User to a Game with a role."""

    __tablename__ = "game_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[MemberRole] = mapped_column(
        Enum(MemberRole, native_enum=False), nullable=False, default=MemberRole.player
    )

    game: Mapped[Game] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")

    __table_args__ = (UniqueConstraint("game_id", "user_id", name="uq_game_member"),)


class Invitation(TimestampMixin, Base):
    """A single-use or revokable invite link for joining a game."""

    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    used_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    game: Mapped[Game] = relationship(back_populates="invitations")


class Act(TimestampMixin, Base):
    """A narrative act within a game, containing scenes."""

    __tablename__ = "acts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    guiding_question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ActStatus] = mapped_column(
        Enum(ActStatus, native_enum=False), nullable=False, default=ActStatus.proposed
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    game: Mapped[Game] = relationship(back_populates="acts")
    scenes: Mapped[list[Scene]] = relationship(back_populates="act", cascade="all, delete-orphan")


class Scene(TimestampMixin, Base):
    """A scene within an act, containing beats and tracked tension."""

    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    act_id: Mapped[int] = mapped_column(ForeignKey("acts.id", ondelete="CASCADE"), nullable=False)
    guiding_question: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[SceneStatus] = mapped_column(
        Enum(SceneStatus, native_enum=False), nullable=False, default=SceneStatus.proposed
    )
    tension: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    act: Mapped[Act] = relationship(back_populates="scenes")
    beats: Mapped[list[Beat]] = relationship(back_populates="scene", cascade="all, delete-orphan")
    characters_present: Mapped[list[Character]] = relationship(
        secondary=scene_characters, back_populates="scenes_present"
    )

    __table_args__ = (
        CheckConstraint("tension >= 1 AND tension <= 9", name="ck_scene_tension_range"),
    )


class Beat(TimestampMixin, Base):
    """A narrative beat within a scene, authored by a player."""

    __tablename__ = "beats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scene_id: Mapped[int] = mapped_column(
        ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    significance: Mapped[BeatSignificance] = mapped_column(
        Enum(BeatSignificance, native_enum=False),
        nullable=False,
        default=BeatSignificance.minor,
    )
    status: Mapped[BeatStatus] = mapped_column(
        Enum(BeatStatus, native_enum=False), nullable=False, default=BeatStatus.proposed
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    scene: Mapped[Scene] = relationship(back_populates="beats")
    author: Mapped[User | None] = relationship(back_populates="beats")
    events: Mapped[list[Event]] = relationship(
        back_populates="beat",
        cascade="all, delete-orphan",
        order_by="Event.order",
    )


class Event(TimestampMixin, Base):
    """A single event within a beat (narrative, roll, oracle, fortune roll, or OOC)."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    beat_id: Mapped[int] = mapped_column(ForeignKey("beats.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[EventType] = mapped_column(Enum(EventType, native_enum=False), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Roll-specific fields
    roll_notation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    roll_result: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Oracle-specific fields
    oracle_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    oracle_interpretations: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Fortune roll-specific fields
    fortune_roll_odds: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fortune_roll_result: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fortune_roll_tension: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Shared: word seeds for oracle and fortune_roll events
    word_seed_action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    word_seed_descriptor: Mapped[str | None] = mapped_column(String(100), nullable=True)

    beat: Mapped[Beat] = relationship(back_populates="events")

    @property
    def interpretations(self) -> list[str]:
        """Return oracle interpretations as a list, deserializing from JSON."""
        if self.oracle_interpretations is None:
            return []
        return json.loads(self.oracle_interpretations)

    @interpretations.setter
    def interpretations(self, value: list[str]) -> None:
        """Serialize and store oracle interpretations as a JSON string."""
        self.oracle_interpretations = json.dumps(value)


class Character(TimestampMixin, Base):
    """A player character in a game."""

    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    game: Mapped[Game] = relationship(back_populates="characters", foreign_keys=[game_id])
    owner: Mapped[User | None] = relationship(back_populates="characters", foreign_keys=[owner_id])
    scenes_present: Mapped[list[Scene]] = relationship(
        secondary=scene_characters, back_populates="characters_present"
    )


class Session0Prompt(TimestampMixin, Base):
    """A single prompt in a game's Session 0 wizard."""

    __tablename__ = "session0_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_safety_tools: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[PromptStatus] = mapped_column(
        Enum(PromptStatus, native_enum=False), nullable=False, default=PromptStatus.pending
    )
    synthesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    synthesis_accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    game: Mapped[Game] = relationship(back_populates="session0_prompts")
    responses: Mapped[list[Session0Response]] = relationship(
        back_populates="prompt", cascade="all, delete-orphan"
    )


class Session0Response(TimestampMixin, Base):
    """A player's contribution to a Session 0 prompt."""

    __tablename__ = "session0_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt_id: Mapped[int] = mapped_column(
        ForeignKey("session0_prompts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    prompt: Mapped[Session0Prompt] = relationship(back_populates="responses")
    user: Mapped[User | None] = relationship()

    __table_args__ = (UniqueConstraint("prompt_id", "user_id", name="uq_session0_response"),)


class GameSafetyTool(TimestampMixin, Base):
    """A line or veil contributed by any member of a game."""

    __tablename__ = "game_safety_tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[SafetyToolKind] = mapped_column(
        Enum(SafetyToolKind, native_enum=False), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)

    game: Mapped[Game] = relationship(back_populates="safety_tools")
    user: Mapped[User | None] = relationship()
