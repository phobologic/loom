"""Tests for AI-Suggested Character Updates (Step 37 / REQ-CHAR-003)."""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loom.models import (
    Act,
    ActStatus,
    Beat,
    BeatStatus,
    Character,
    CharacterUpdateCategory,
    CharacterUpdateStatus,
    CharacterUpdateSuggestion,
    Event,
    EventType,
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    Notification,
    NotificationType,
    ProposalType,
    Scene,
    SceneStatus,
    VoteProposal,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


async def _login(client: AsyncClient, user_id: int) -> None:
    await client.post("/dev/login", data={"user_id": str(user_id)}, follow_redirects=False)


async def _create_active_game(client: AsyncClient, db: AsyncSession) -> int:
    """Create a single-player active game as Alice (user 1)."""
    await _login(client, 1)
    r = await client.post(
        "/games", data={"name": "Suggestion Test Game", "pitch": "A pitch"}, follow_redirects=False
    )
    game_id = int(r.headers["location"].rsplit("/", 1)[-1])
    await client.post(f"/games/{game_id}/session0/propose-ready", follow_redirects=False)
    return game_id


async def _create_character(
    game_id: int,
    owner_id: int,
    db: AsyncSession,
    *,
    name: str = "Hero",
    notes: str | None = None,
) -> int:
    char = Character(game_id=game_id, owner_id=owner_id, name=name, notes=notes)
    db.add(char)
    await db.commit()
    return char.id


async def _create_active_scene(game_id: int, db: AsyncSession) -> tuple[int, int]:
    """Create an act and an active scene; return (act_id, scene_id)."""
    act = Act(
        game_id=game_id, guiding_question="What lurks here?", status=ActStatus.active, order=1
    )
    db.add(act)
    await db.flush()
    scene = Scene(
        act_id=act.id,
        guiding_question="What happens next?",
        status=SceneStatus.active,
        order=1,
        tension=5,
    )
    db.add(scene)
    await db.commit()
    return act.id, scene.id


async def _create_suggestion(
    character_id: int,
    db: AsyncSession,
    *,
    scene_id: int | None = None,
    category: CharacterUpdateCategory = CharacterUpdateCategory.trait,
    suggestion_text: str = "Showed courage under pressure.",
    reason: str = "Beat #1 showed bravery.",
    beat_ids: list[int] | None = None,
    status: CharacterUpdateStatus = CharacterUpdateStatus.pending,
) -> int:
    sug = CharacterUpdateSuggestion(
        character_id=character_id,
        scene_id=scene_id,
        category=category,
        suggestion_text=suggestion_text,
        reason=reason,
        referenced_beat_ids=json.dumps(beat_ids) if beat_ids else None,
        status=status,
    )
    db.add(sug)
    await db.commit()
    return sug.id


# ---------------------------------------------------------------------------
# Model — CharacterUpdateSuggestion
# ---------------------------------------------------------------------------


class TestCharacterUpdateSuggestionModel:
    async def test_suggestion_persists(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        char = Character(game_id=game_id, owner_id=1, name="TestChar")
        db.add(char)
        await db.flush()

        sug = CharacterUpdateSuggestion(
            character_id=char.id,
            category=CharacterUpdateCategory.relationship,
            suggestion_text="Bonded with the innkeeper.",
            reason="Beat #5 showed trust.",
            referenced_beat_ids=json.dumps([5, 6]),
            status=CharacterUpdateStatus.pending,
        )
        db.add(sug)
        await db.flush()

        result = await db.scalar(
            select(CharacterUpdateSuggestion).where(CharacterUpdateSuggestion.id == sug.id)
        )
        assert result is not None
        assert result.category == CharacterUpdateCategory.relationship
        assert result.beat_ids == [5, 6]
        assert result.status == CharacterUpdateStatus.pending

    async def test_beat_ids_property_empty_when_null(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        char = Character(game_id=game_id, owner_id=1, name="NoBeatChar")
        db.add(char)
        await db.flush()

        sug = CharacterUpdateSuggestion(
            character_id=char.id,
            category=CharacterUpdateCategory.goal,
            suggestion_text="Changed motivation.",
            reason="General arc.",
            referenced_beat_ids=None,
            status=CharacterUpdateStatus.pending,
        )
        db.add(sug)
        await db.flush()
        assert sug.beat_ids == []


# ---------------------------------------------------------------------------
# GET /games/{game_id}/characters/{char_id}/suggestions
# ---------------------------------------------------------------------------


class TestSuggestionsPage:
    async def test_requires_auth(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db)
        # Log out by logging in as nobody — just hit without auth cookie
        await client.post("/dev/login", data={"user_id": "999"}, follow_redirects=False)
        r = await client.get(
            f"/games/{game_id}/characters/{char_id}/suggestions", follow_redirects=False
        )
        # 999 is not a member
        assert r.status_code in (302, 401, 403, 404)

    async def test_requires_membership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db)
        await _login(client, 2)  # Bob is not a member
        r = await client.get(
            f"/games/{game_id}/characters/{char_id}/suggestions", follow_redirects=False
        )
        assert r.status_code == 403

    async def test_requires_ownership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        # Alice owns char; add Bob as member
        char_id = await _create_character(game_id, 1, db)
        db.add(GameMember(game_id=game_id, user_id=2, role=MemberRole.player))
        await db.commit()
        await _login(client, 2)  # Bob accesses Alice's char
        r = await client.get(
            f"/games/{game_id}/characters/{char_id}/suggestions", follow_redirects=False
        )
        assert r.status_code == 403

    async def test_empty_state_for_owner(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db)
        await _login(client, 1)
        r = await client.get(
            f"/games/{game_id}/characters/{char_id}/suggestions", follow_redirects=False
        )
        assert r.status_code == 200
        assert b"No pending suggestions" in r.content

    async def test_shows_pending_suggestions(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db)
        sug_id = await _create_suggestion(char_id, db, suggestion_text="Gained a scar.")
        await _login(client, 1)
        r = await client.get(
            f"/games/{game_id}/characters/{char_id}/suggestions", follow_redirects=False
        )
        assert r.status_code == 200
        assert b"Gained a scar." in r.content
        assert b"Beat #1" in r.content or b"showed bravery" in r.content.lower()

    async def test_does_not_show_resolved_suggestions(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db)
        await _create_suggestion(
            char_id, db, suggestion_text="Dismissed item.", status=CharacterUpdateStatus.dismissed
        )
        await _login(client, 1)
        r = await client.get(
            f"/games/{game_id}/characters/{char_id}/suggestions", follow_redirects=False
        )
        assert r.status_code == 200
        assert b"Dismissed item." not in r.content


# ---------------------------------------------------------------------------
# POST …/suggestions/{sug_id}/accept
# ---------------------------------------------------------------------------


class TestAcceptSuggestion:
    async def test_accept_sets_status_and_stores_text(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db)
        sug_id = await _create_suggestion(char_id, db, suggestion_text="Original suggestion.")
        await _login(client, 1)
        r = await client.post(
            f"/games/{game_id}/characters/{char_id}/suggestions/{sug_id}/accept",
            data={"applied_text": ""},
            follow_redirects=False,
        )
        assert r.status_code == 200

        db.expire_all()
        sug = await db.scalar(
            select(CharacterUpdateSuggestion).where(CharacterUpdateSuggestion.id == sug_id)
        )
        assert sug is not None
        assert sug.status == CharacterUpdateStatus.accepted
        assert sug.applied_text == "Original suggestion."

    async def test_accept_with_custom_text(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db)
        sug_id = await _create_suggestion(char_id, db)
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/characters/{char_id}/suggestions/{sug_id}/accept",
            data={"applied_text": "My edited version."},
            follow_redirects=False,
        )
        db.expire_all()
        sug = await db.scalar(
            select(CharacterUpdateSuggestion).where(CharacterUpdateSuggestion.id == sug_id)
        )
        assert sug is not None
        assert sug.applied_text == "My edited version."

    async def test_accept_does_not_modify_character_notes(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db, notes="Original player notes.")
        sug_id = await _create_suggestion(char_id, db, suggestion_text="AI suggestion.")
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/characters/{char_id}/suggestions/{sug_id}/accept",
            data={"applied_text": ""},
            follow_redirects=False,
        )
        db.expire_all()
        char = await db.scalar(select(Character).where(Character.id == char_id))
        assert char is not None
        assert char.notes == "Original player notes."

    async def test_accept_requires_ownership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db)
        sug_id = await _create_suggestion(char_id, db)
        db.add(GameMember(game_id=game_id, user_id=2, role=MemberRole.player))
        await db.commit()
        await _login(client, 2)
        r = await client.post(
            f"/games/{game_id}/characters/{char_id}/suggestions/{sug_id}/accept",
            data={"applied_text": ""},
            follow_redirects=False,
        )
        assert r.status_code == 403

    async def test_accept_already_accepted_returns_409(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db)
        sug_id = await _create_suggestion(char_id, db, status=CharacterUpdateStatus.accepted)
        await _login(client, 1)
        r = await client.post(
            f"/games/{game_id}/characters/{char_id}/suggestions/{sug_id}/accept",
            data={"applied_text": ""},
            follow_redirects=False,
        )
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# POST …/suggestions/{sug_id}/dismiss
# ---------------------------------------------------------------------------


class TestDismissSuggestion:
    async def test_dismiss_sets_status(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db, notes="Keep this.")
        sug_id = await _create_suggestion(char_id, db)
        await _login(client, 1)
        r = await client.post(
            f"/games/{game_id}/characters/{char_id}/suggestions/{sug_id}/dismiss",
            follow_redirects=False,
        )
        assert r.status_code == 200

        db.expire_all()
        sug = await db.scalar(
            select(CharacterUpdateSuggestion).where(CharacterUpdateSuggestion.id == sug_id)
        )
        assert sug is not None
        assert sug.status == CharacterUpdateStatus.dismissed

    async def test_dismiss_does_not_modify_notes(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db, notes="Untouched notes.")
        sug_id = await _create_suggestion(char_id, db)
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/characters/{char_id}/suggestions/{sug_id}/dismiss",
            follow_redirects=False,
        )
        db.expire_all()
        char = await db.scalar(select(Character).where(Character.id == char_id))
        assert char is not None
        assert char.notes == "Untouched notes."

    async def test_dismiss_requires_ownership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db)
        sug_id = await _create_suggestion(char_id, db)
        db.add(GameMember(game_id=game_id, user_id=2, role=MemberRole.player))
        await db.commit()
        await _login(client, 2)
        r = await client.post(
            f"/games/{game_id}/characters/{char_id}/suggestions/{sug_id}/dismiss",
            follow_redirects=False,
        )
        assert r.status_code == 403

    async def test_dismiss_already_dismissed_returns_409(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await _create_active_game(client, db)
        char_id = await _create_character(game_id, 1, db)
        sug_id = await _create_suggestion(char_id, db, status=CharacterUpdateStatus.dismissed)
        await _login(client, 1)
        r = await client.post(
            f"/games/{game_id}/characters/{char_id}/suggestions/{sug_id}/dismiss",
            follow_redirects=False,
        )
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# Scene completion integration
# ---------------------------------------------------------------------------


class TestSceneCompletionHook:
    async def _create_two_player_game(self, client: AsyncClient, db: AsyncSession) -> int:
        """Create a 2-player active game (Alice + Bob) so completion goes through cast_vote."""
        await _login(client, 1)
        r = await client.post(
            "/games", data={"name": "Hook Test Game", "pitch": "A pitch"}, follow_redirects=False
        )
        game_id = int(r.headers["location"].rsplit("/", 1)[-1])
        db.add(GameMember(game_id=game_id, user_id=2, role=MemberRole.player))
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one()
        game.status = GameStatus.active
        await db.commit()
        return game_id

    async def _complete_scene_two_player(
        self,
        client: AsyncClient,
        db: AsyncSession,
        game_id: int,
        act_id: int,
        scene_id: int,
    ) -> None:
        """Alice proposes scene_complete; Bob votes yes → cast_vote fires, applies outcome."""
        await _login(client, 1)
        await client.post(
            f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/complete",
            follow_redirects=False,
        )
        db.expire_all()
        proposal = await db.scalar(
            select(VoteProposal).where(
                VoteProposal.game_id == game_id,
                VoteProposal.proposal_type == ProposalType.scene_complete,
            )
        )
        assert proposal is not None, "Expected scene_complete proposal to exist"
        await _login(client, 2)
        await client.post(
            f"/games/{game_id}/proposals/{proposal.id}/vote",
            data={"choice": "yes"},
            follow_redirects=False,
        )

    async def test_scene_complete_creates_suggestions(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ) -> None:
        """When mock returns suggestions, rows are created after scene completion."""
        game_id = await self._create_two_player_game(client, db)
        char_id = await _create_character(game_id, 1, db, name="Alice's Hero")
        act_id, scene_id = await _create_active_scene(game_id, db)

        async def _suggest(game, scene, character, *, db=None, game_id=None):
            return [("trait", "Showed courage under fire.", "Beat #42 showed bravery.", [42])]

        monkeypatch.setattr("loom.routers.world_document._ai_suggest_character_updates", _suggest)

        await self._complete_scene_two_player(client, db, game_id, act_id, scene_id)

        db.expire_all()
        suggestions = list(
            await db.scalars(
                select(CharacterUpdateSuggestion).where(
                    CharacterUpdateSuggestion.character_id == char_id
                )
            )
        )
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s.category == CharacterUpdateCategory.trait
        assert s.suggestion_text == "Showed courage under fire."
        assert s.reason == "Beat #42 showed bravery."
        assert s.beat_ids == [42]
        assert s.status == CharacterUpdateStatus.pending

    async def test_scene_complete_sends_notification(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ) -> None:
        """Character owner receives a character_update_suggested notification."""
        game_id = await self._create_two_player_game(client, db)
        char_id = await _create_character(game_id, 1, db)
        act_id, scene_id = await _create_active_scene(game_id, db)

        async def _suggest(game, scene, character, *, db=None, game_id=None):
            return [("goal", "New goal.", "General scene arc.", [])]

        monkeypatch.setattr("loom.routers.world_document._ai_suggest_character_updates", _suggest)

        await self._complete_scene_two_player(client, db, game_id, act_id, scene_id)

        db.expire_all()
        notifications = list(
            await db.scalars(
                select(Notification).where(
                    Notification.user_id == 1,
                    Notification.notification_type == NotificationType.character_update_suggested,
                )
            )
        )
        assert len(notifications) >= 1
        assert f"/games/{game_id}/characters/{char_id}/suggestions" in notifications[0].link

    async def test_scene_complete_skips_unowned_characters(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ) -> None:
        """NPCs (no owner_id) do not receive suggestions."""
        game_id = await self._create_two_player_game(client, db)
        npc = Character(game_id=game_id, owner_id=None, name="NPC Guard")
        db.add(npc)
        await db.commit()
        npc_id = npc.id

        act_id, scene_id = await _create_active_scene(game_id, db)
        call_count = {"n": 0}

        async def _suggest(game, scene, character, *, db=None, game_id=None):
            call_count["n"] += 1
            return [("trait", "Something.", "A beat.", [])]

        monkeypatch.setattr("loom.routers.world_document._ai_suggest_character_updates", _suggest)

        await self._complete_scene_two_player(client, db, game_id, act_id, scene_id)

        # AI should NOT be called for the NPC
        assert call_count["n"] == 0

        db.expire_all()
        rows = list(
            await db.scalars(
                select(CharacterUpdateSuggestion).where(
                    CharacterUpdateSuggestion.character_id == npc_id
                )
            )
        )
        assert rows == []

    async def test_scene_complete_ai_failure_does_not_abort(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ) -> None:
        """AI RuntimeError is swallowed; scene still becomes complete."""
        game_id = await self._create_two_player_game(client, db)
        await _create_character(game_id, 1, db)
        act_id, scene_id = await _create_active_scene(game_id, db)

        async def _suggest_fails(game, scene, character, *, db=None, game_id=None):
            raise RuntimeError("AI unavailable")

        monkeypatch.setattr(
            "loom.routers.world_document._ai_suggest_character_updates", _suggest_fails
        )

        await self._complete_scene_two_player(client, db, game_id, act_id, scene_id)

        db.expire_all()
        scene = await db.scalar(select(Scene).where(Scene.id == scene_id))
        assert scene is not None
        assert scene.status == SceneStatus.complete

    async def test_scene_complete_no_suggestions_when_no_owned_chars(
        self, client: AsyncClient, db: AsyncSession, monkeypatch
    ) -> None:
        """Game with no owned characters produces no suggestion rows."""
        game_id = await self._create_two_player_game(client, db)
        # No characters at all
        act_id, scene_id = await _create_active_scene(game_id, db)

        called = {"n": 0}

        async def _suggest(game, scene, character, *, db=None, game_id=None):
            called["n"] += 1
            return []

        monkeypatch.setattr("loom.routers.world_document._ai_suggest_character_updates", _suggest)

        await self._complete_scene_two_player(client, db, game_id, act_id, scene_id)

        assert called["n"] == 0
