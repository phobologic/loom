"""Tests for AI-Suggested World Entries (Step 44 / REQ-WORLD-002)."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loom.models import (
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    Notification,
    NotificationType,
    WorldEntry,
    WorldEntrySuggestion,
    WorldEntrySuggestionStatus,
    WorldEntryType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _login(client: AsyncClient, user_id: int) -> None:
    await client.post("/dev/login", data={"user_id": str(user_id)}, follow_redirects=False)


async def _create_game(client: AsyncClient, name: str = "Suggestion Test Game") -> int:
    r = await client.post("/games", data={"name": name, "pitch": ""}, follow_redirects=False)
    assert r.status_code == 303
    return int(r.headers["location"].rsplit("/", 1)[-1])


async def _activate_game(db: AsyncSession, game_id: int) -> None:
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one()
    game.status = GameStatus.active
    await db.commit()


async def _add_member(
    db: AsyncSession, game_id: int, user_id: int, role: MemberRole = MemberRole.player
) -> None:
    db.add(GameMember(game_id=game_id, user_id=user_id, role=role))
    await db.commit()


async def _seed_suggestion(
    db: AsyncSession,
    game_id: int,
    *,
    name: str = "The Spire",
    entry_type: WorldEntryType = WorldEntryType.location,
    description: str = "A tall tower in the city centre.",
    reason: str = "Named location introduced in the beat.",
    status: WorldEntrySuggestionStatus = WorldEntrySuggestionStatus.pending,
) -> WorldEntrySuggestion:
    sug = WorldEntrySuggestion(
        game_id=game_id,
        suggested_type=entry_type,
        suggested_name=name,
        suggested_description=description,
        reason=reason,
        status=status,
    )
    db.add(sug)
    await db.commit()
    return sug


# ---------------------------------------------------------------------------
# Page rendering
# ---------------------------------------------------------------------------


class TestSuggestionsOnPage:
    async def _setup(self, client: AsyncClient, db: AsyncSession) -> int:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        return game_id

    async def test_page_shows_pending_suggestions(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await self._setup(client, db)
        await _seed_suggestion(db, game_id, name="The Iron Gate")

        db.expire_all()
        response = await client.get(f"/games/{game_id}/world-entries")
        assert response.status_code == 200
        assert "AI Suggestions" in response.text
        assert "The Iron Gate" in response.text

    async def test_dismissed_suggestions_not_shown(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await self._setup(client, db)
        await _seed_suggestion(
            db, game_id, name="Ghost Town", status=WorldEntrySuggestionStatus.dismissed
        )

        db.expire_all()
        response = await client.get(f"/games/{game_id}/world-entries")
        assert response.status_code == 200
        assert "Ghost Town" not in response.text

    async def test_accepted_suggestions_not_shown(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await self._setup(client, db)
        await _seed_suggestion(
            db, game_id, name="Old Keep", status=WorldEntrySuggestionStatus.accepted
        )

        db.expire_all()
        response = await client.get(f"/games/{game_id}/world-entries")
        assert response.status_code == 200
        assert "Old Keep" not in response.text

    async def test_no_suggestions_section_when_empty(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await self._setup(client, db)
        response = await client.get(f"/games/{game_id}/world-entries")
        assert response.status_code == 200
        assert "AI Suggestions" not in response.text


# ---------------------------------------------------------------------------
# Accept
# ---------------------------------------------------------------------------


class TestAcceptSuggestion:
    async def _setup(self, client: AsyncClient, db: AsyncSession) -> tuple[int, int]:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        sug = await _seed_suggestion(
            db, game_id, name="The Library", entry_type=WorldEntryType.location
        )
        return game_id, sug.id

    async def test_accept_creates_world_entry(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, sug_id = await self._setup(client, db)

        response = await client.post(
            f"/games/{game_id}/world-entry-suggestions/{sug_id}/accept",
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        entries = list(
            (await db.execute(select(WorldEntry).where(WorldEntry.game_id == game_id))).scalars()
        )
        assert any(e.name == "The Library" for e in entries)

    async def test_accept_marks_suggestion_accepted(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, sug_id = await self._setup(client, db)

        await client.post(
            f"/games/{game_id}/world-entry-suggestions/{sug_id}/accept",
            follow_redirects=False,
        )

        db.expire_all()
        result = await db.execute(
            select(WorldEntrySuggestion).where(WorldEntrySuggestion.id == sug_id)
        )
        sug = result.scalar_one()
        assert sug.status == WorldEntrySuggestionStatus.accepted

    async def test_accept_sends_notification(self, client: AsyncClient, db: AsyncSession) -> None:
        """Accepting a suggestion notifies other members via world_entry_created."""
        game_id, sug_id = await self._setup(client, db)
        await _add_member(db, game_id, 2)

        await client.post(
            f"/games/{game_id}/world-entry-suggestions/{sug_id}/accept",
            follow_redirects=False,
        )

        db.expire_all()
        result = await db.execute(
            select(Notification)
            .where(Notification.game_id == game_id)
            .where(Notification.notification_type == NotificationType.world_entry_created)
            .where(Notification.user_id == 2)
        )
        notifications = list(result.scalars())
        assert len(notifications) == 1
        assert "The Library" in notifications[0].message

    async def test_accept_requires_membership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, sug_id = await self._setup(client, db)
        await _login(client, 2)

        response = await client.post(
            f"/games/{game_id}/world-entry-suggestions/{sug_id}/accept",
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_any_member_can_accept(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, sug_id = await self._setup(client, db)
        await _add_member(db, game_id, 2)
        await _login(client, 2)

        response = await client.post(
            f"/games/{game_id}/world-entry-suggestions/{sug_id}/accept",
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_accept_already_accepted_returns_404(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, sug_id = await self._setup(client, db)
        # Accept once
        await client.post(
            f"/games/{game_id}/world-entry-suggestions/{sug_id}/accept",
            follow_redirects=False,
        )
        # Try again
        response = await client.post(
            f"/games/{game_id}/world-entry-suggestions/{sug_id}/accept",
            follow_redirects=False,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Dismiss
# ---------------------------------------------------------------------------


class TestDismissSuggestion:
    async def _setup(self, client: AsyncClient, db: AsyncSession) -> tuple[int, int]:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        sug = await _seed_suggestion(db, game_id, name="Dead End Alley")
        return game_id, sug.id

    async def test_dismiss_marks_suggestion_dismissed(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, sug_id = await self._setup(client, db)

        response = await client.post(
            f"/games/{game_id}/world-entry-suggestions/{sug_id}/dismiss",
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        result = await db.execute(
            select(WorldEntrySuggestion).where(WorldEntrySuggestion.id == sug_id)
        )
        sug = result.scalar_one()
        assert sug.status == WorldEntrySuggestionStatus.dismissed

    async def test_dismiss_does_not_create_entry(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, sug_id = await self._setup(client, db)

        await client.post(
            f"/games/{game_id}/world-entry-suggestions/{sug_id}/dismiss",
            follow_redirects=False,
        )

        db.expire_all()
        entries = list(
            (await db.execute(select(WorldEntry).where(WorldEntry.game_id == game_id))).scalars()
        )
        assert not any(e.name == "Dead End Alley" for e in entries)

    async def test_dismiss_requires_membership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, sug_id = await self._setup(client, db)
        await _login(client, 2)

        response = await client.post(
            f"/games/{game_id}/world-entry-suggestions/{sug_id}/dismiss",
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_any_member_can_dismiss(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, sug_id = await self._setup(client, db)
        await _add_member(db, game_id, 2)
        await _login(client, 2)

        response = await client.post(
            f"/games/{game_id}/world-entry-suggestions/{sug_id}/dismiss",
            follow_redirects=False,
        )
        assert response.status_code == 303

    async def test_dismiss_already_dismissed_returns_404(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, sug_id = await self._setup(client, db)
        await client.post(
            f"/games/{game_id}/world-entry-suggestions/{sug_id}/dismiss",
            follow_redirects=False,
        )
        response = await client.post(
            f"/games/{game_id}/world-entry-suggestions/{sug_id}/dismiss",
            follow_redirects=False,
        )
        assert response.status_code == 404


