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
    """How tied oracle interpretation votes are resolved."""

    random = "random"
    proposer = "proposer"


class OracleType(str, enum.Enum):
    """Whether an oracle invocation is personal or world-affecting."""

    personal = "personal"  # affects invoker's character only — invoker selects immediately
    world = "world"  # affects shared fiction — collaborative discussion + selection


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


class ProposalType(str, enum.Enum):
    """What is being voted on."""

    world_doc_approval = "world_doc_approval"
    ready_to_play = "ready_to_play"
    act_proposal = "act_proposal"
    scene_proposal = "scene_proposal"
    beat_proposal = "beat_proposal"
    scene_complete = "scene_complete"
    act_complete = "act_complete"
    tension_adjustment = "tension_adjustment"


class ProposalStatus(str, enum.Enum):
    """Lifecycle status of a vote proposal."""

    open = "open"
    approved = "approved"
    rejected = "rejected"
    withdrawn = "withdrawn"


class VoteChoice(str, enum.Enum):
    """A player's vote on a proposal."""

    yes = "yes"
    no = "no"
    suggest_modification = "suggest_modification"


class WordSeedWordType(str, enum.Enum):
    """Whether a word seed is an action/verb or a descriptor/subject."""

    action = "action"
    descriptor = "descriptor"


class EmailPref(str, enum.Enum):
    """User email notification preference."""

    immediate = "immediate"
    digest = "digest"
    off = "off"


class NotificationType(str, enum.Enum):
    """Category of in-app notification."""

    new_beat = "new_beat"
    vote_required = "vote_required"
    oracle_ready = "oracle_ready"
    beat_challenged = "beat_challenged"
    beat_approved = "beat_approved"
    fortune_roll_contested = "fortune_roll_contested"
    act_proposed = "act_proposed"
    scene_proposed = "scene_proposed"
    challenge_dismissed = "challenge_dismissed"
    beat_revised = "beat_revised"
    beat_comment_added = "beat_comment_added"
    spotlight = "spotlight"
    character_update_suggested = "character_update_suggested"
    npc_created = "npc_created"
    world_entry_created = "world_entry_created"


class WorldEntryType(str, enum.Enum):
    """Type of world entry."""

    location = "location"
    faction = "faction"
    item = "item"
    concept = "concept"
    other = "other"


class CharacterUpdateCategory(str, enum.Enum):
    """Category of AI-suggested character update."""

    relationship = "relationship"
    trait = "trait"
    item = "item"
    goal = "goal"


class CharacterUpdateStatus(str, enum.Enum):
    """Lifecycle status of a character update suggestion."""

    pending = "pending"
    accepted = "accepted"
    dismissed = "dismissed"


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
    __table_args__ = (UniqueConstraint("oauth_provider", "oauth_subject", name="uq_users_oauth"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    oauth_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notify_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_pref: Mapped[EmailPref] = mapped_column(
        Enum(EmailPref, native_enum=False), nullable=False, default=EmailPref.digest
    )
    prose_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="always", server_default="always"
    )
    prose_threshold_words: Mapped[int] = mapped_column(
        Integer, nullable=False, default=50, server_default="50"
    )

    memberships: Mapped[list[GameMember]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    characters: Mapped[list[Character]] = relationship(
        back_populates="owner",
        foreign_keys="Character.owner_id",
    )
    beats: Mapped[list[Beat]] = relationship(
        back_populates="author", foreign_keys="[Beat.author_id]"
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Notification.created_at.desc()",
    )


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
    world_document: Mapped[WorldDocument | None] = relationship(
        back_populates="game",
        uselist=False,
        cascade="all, delete-orphan",
    )
    proposals: Mapped[list[VoteProposal]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="VoteProposal.created_at",
    )
    word_seed_tables: Mapped[list[WordSeedTable]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
    )
    npcs: Mapped[list[NPC]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="NPC.name",
    )
    world_entries: Mapped[list[WorldEntry]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="WorldEntry.entry_type, WorldEntry.name",
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
    prose_mode_override: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email_pref_override: Mapped[str | None] = mapped_column(String(20), nullable=True)

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
    tension_carry_forward: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
    challenge_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    challenge_outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    challenged_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    waiting_for_character_id: Mapped[int | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL"), nullable=True
    )
    spotlight_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    spotlight_resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    scene: Mapped[Scene] = relationship(back_populates="beats")
    author: Mapped[User | None] = relationship(
        back_populates="beats", foreign_keys="[Beat.author_id]"
    )
    challenged_by: Mapped[User | None] = relationship(foreign_keys="[Beat.challenged_by_id]")
    waiting_for_character: Mapped["Character | None"] = relationship(
        foreign_keys="[Beat.waiting_for_character_id]"
    )
    events: Mapped[list[Event]] = relationship(
        back_populates="beat",
        cascade="all, delete-orphan",
        order_by="Event.order",
    )
    comments: Mapped[list[BeatComment]] = relationship(
        back_populates="beat",
        cascade="all, delete-orphan",
        order_by="BeatComment.created_at",
    )


class BeatComment(TimestampMixin, Base):
    """A discussion comment on a challenged beat."""

    __tablename__ = "beat_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    beat_id: Mapped[int] = mapped_column(ForeignKey("beats.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    beat: Mapped[Beat] = relationship(back_populates="comments")
    author: Mapped[User | None] = relationship()


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
    fortune_roll_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    fortune_roll_contested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    # Shared: word seeds for oracle and fortune_roll events
    word_seed_action: Mapped[str | None] = mapped_column(String(100), nullable=True)
    word_seed_descriptor: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Oracle discussion fields
    oracle_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    oracle_selected_interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Prose expansion fields (REQ-PROSE-001)
    prose_expanded: Mapped[str | None] = mapped_column(Text, nullable=True)
    prose_applied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    prose_dismissed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    beat: Mapped[Beat] = relationship(back_populates="events")
    oracle_interpretation_votes: Mapped[list[OracleInterpretationVote]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="OracleInterpretationVote.created_at",
    )
    oracle_comments: Mapped[list[OracleComment]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="OracleComment.created_at",
    )

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
    voice_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    game: Mapped[Game] = relationship(back_populates="characters", foreign_keys=[game_id])
    owner: Mapped[User | None] = relationship(back_populates="characters", foreign_keys=[owner_id])
    scenes_present: Mapped[list[Scene]] = relationship(
        secondary=scene_characters, back_populates="characters_present"
    )
    update_suggestions: Mapped[list[CharacterUpdateSuggestion]] = relationship(
        back_populates="character",
        cascade="all, delete-orphan",
        order_by="CharacterUpdateSuggestion.created_at",
    )


class NPC(TimestampMixin, Base):
    """A non-player character tracked collaboratively by all game members."""

    __tablename__ = "npcs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    game: Mapped[Game] = relationship(back_populates="npcs")


class WorldEntry(TimestampMixin, Base):
    """A shared wiki-like world entry (location, faction, item, concept, etc.)."""

    __tablename__ = "world_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    entry_type: Mapped[WorldEntryType] = mapped_column(
        Enum(WorldEntryType, native_enum=False), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    game: Mapped[Game] = relationship(back_populates="world_entries")


class CharacterUpdateSuggestion(TimestampMixin, Base):
    """An AI-generated suggestion for updating a character sheet after a scene."""

    __tablename__ = "character_update_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False
    )
    scene_id: Mapped[int | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[CharacterUpdateCategory] = mapped_column(
        Enum(CharacterUpdateCategory, native_enum=False), nullable=False
    )
    suggestion_text: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    referenced_beat_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    applied_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CharacterUpdateStatus] = mapped_column(
        Enum(CharacterUpdateStatus, native_enum=False),
        nullable=False,
        default=CharacterUpdateStatus.pending,
    )

    character: Mapped[Character] = relationship(back_populates="update_suggestions")
    scene: Mapped[Scene | None] = relationship()

    @property
    def beat_ids(self) -> list[int]:
        """Parsed list of referenced beat IDs (empty if none)."""
        if self.referenced_beat_ids is None:
            return []
        return json.loads(self.referenced_beat_ids)


class Session0Prompt(TimestampMixin, Base):
    """A single prompt in a game's Session 0 wizard."""

    __tablename__ = "session0_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_safety_tools: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_word_seeds: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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


class WorldDocument(TimestampMixin, Base):
    """The generated world document capturing agreed-upon setting for a game."""

    __tablename__ = "world_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    game: Mapped[Game] = relationship(back_populates="world_document")


class VoteProposal(TimestampMixin, Base):
    """A proposal subject to group approval via votes."""

    __tablename__ = "vote_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    proposal_type: Mapped[ProposalType] = mapped_column(
        Enum(ProposalType, native_enum=False), nullable=False
    )
    proposed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus, native_enum=False), nullable=False, default=ProposalStatus.open
    )

    act_id: Mapped[int | None] = mapped_column(
        ForeignKey("acts.id", ondelete="SET NULL"), nullable=True
    )
    scene_id: Mapped[int | None] = mapped_column(
        ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True
    )
    beat_id: Mapped[int | None] = mapped_column(
        ForeignKey("beats.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tension_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    game: Mapped[Game] = relationship(back_populates="proposals")
    proposed_by: Mapped[User | None] = relationship(foreign_keys=[proposed_by_id])
    act: Mapped[Act | None] = relationship(foreign_keys=[act_id])
    scene: Mapped[Scene | None] = relationship(foreign_keys=[scene_id])
    beat: Mapped[Beat | None] = relationship(foreign_keys=[beat_id])
    votes: Mapped[list[Vote]] = relationship(
        back_populates="proposal",
        cascade="all, delete-orphan",
        order_by="Vote.created_at",
    )


class Vote(TimestampMixin, Base):
    """An individual player's vote on a VoteProposal."""

    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proposal_id: Mapped[int] = mapped_column(
        ForeignKey("vote_proposals.id", ondelete="CASCADE"), nullable=False
    )
    voter_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    choice: Mapped[VoteChoice] = mapped_column(Enum(VoteChoice, native_enum=False), nullable=False)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)

    proposal: Mapped[VoteProposal] = relationship(back_populates="votes")
    voter: Mapped[User | None] = relationship()

    __table_args__ = (UniqueConstraint("proposal_id", "voter_id", name="uq_vote"),)


class OracleInterpretationVote(TimestampMixin, Base):
    """A player's vote for a particular oracle interpretation."""

    __tablename__ = "oracle_interpretation_votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    voter_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # 0-based index into event.interpretations; -1 means a custom alternative
    interpretation_index: Mapped[int] = mapped_column(Integer, nullable=False)
    alternative_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    event: Mapped[Event] = relationship(back_populates="oracle_interpretation_votes")
    voter: Mapped[User | None] = relationship()

    __table_args__ = (UniqueConstraint("event_id", "voter_id", name="uq_oracle_vote"),)


class OracleComment(TimestampMixin, Base):
    """A player's comment on an oracle invocation."""

    __tablename__ = "oracle_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)

    event: Mapped[Event] = relationship(back_populates="oracle_comments")
    author: Mapped[User | None] = relationship()


class WordSeedTable(TimestampMixin, Base):
    """A themed set of word seeds available for oracle invocations in a game."""

    __tablename__ = "word_seed_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    game: Mapped[Game] = relationship(back_populates="word_seed_tables")
    entries: Mapped[list[WordSeedEntry]] = relationship(
        back_populates="table",
        cascade="all, delete-orphan",
    )


class WordSeedEntry(TimestampMixin, Base):
    """A single word within a WordSeedTable."""

    __tablename__ = "word_seed_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_id: Mapped[int] = mapped_column(
        ForeignKey("word_seed_tables.id", ondelete="CASCADE"), nullable=False
    )
    word: Mapped[str] = mapped_column(String(100), nullable=False)
    word_type: Mapped[WordSeedWordType] = mapped_column(
        Enum(WordSeedWordType, native_enum=False), nullable=False
    )

    table: Mapped[WordSeedTable] = relationship(back_populates="entries")


class AIUsageLog(Base):
    """A log entry for every AI model call made by the system.

    Stores the feature that triggered the call, token counts, context
    components included, and model used. Not exposed to players in v1.
    """

    __tablename__ = "ai_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    feature: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    # JSON-encoded list of context component names included in the prompt
    context_components: Mapped[str | None] = mapped_column(Text, nullable=True)
    game_id: Mapped[int | None] = mapped_column(
        ForeignKey("games.id", ondelete="SET NULL"), nullable=True
    )

    game: Mapped[Game | None] = relationship()


class Notification(TimestampMixin, Base):
    """A per-user in-app notification for a game event."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    game_id: Mapped[int | None] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=True
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, native_enum=False), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="notifications")
    game: Mapped[Game | None] = relationship()
