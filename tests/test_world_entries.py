"""Tests for world entry creation and management routes."""

from __future__ import annotations

import pytest
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
    WorldEntryType,
)


async def _login(client: AsyncClient, user_id: int) -> None:
    await client.post("/dev/login", data={"user_id": str(user_id)}, follow_redirects=False)


async def _create_game(client: AsyncClient, name: str = "Test Game") -> int:
    response = await client.post("/games", data={"name": name, "pitch": ""}, follow_redirects=False)
    assert response.status_code == 303
    location = response.headers["location"]
    return int(location.rsplit("/", 1)[-1])


async def _add_member(
    db: AsyncSession, game_id: int, user_id: int, role: MemberRole = MemberRole.player
) -> None:
    db.add(GameMember(game_id=game_id, user_id=user_id, role=role))
    await db.commit()


async def _activate_game(db: AsyncSession, game_id: int) -> None:
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one()
    game.status = GameStatus.active
    await db.commit()


async def _get_entries(db: AsyncSession, game_id: int) -> list[WorldEntry]:
    result = await db.execute(
        select(WorldEntry)
        .where(WorldEntry.game_id == game_id)
        .order_by(WorldEntry.entry_type, WorldEntry.name)
    )
    return list(result.scalars().all())


async def _create_entry(
    client: AsyncClient,
    game_id: int,
    name: str = "The Old Mill",
    entry_type: str = "location",
    description: str = "A crumbling mill on the river.",
) -> int:
    response = await client.post(
        f"/games/{game_id}/world-entries",
        data={"name": name, "entry_type": entry_type, "description": description},
        follow_redirects=False,
    )
    return response.status_code


class TestWorldEntriesPage:
    async def _setup(self, client: AsyncClient, db: AsyncSession) -> int:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        return game_id

    async def test_page_loads_for_member(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client, db)
        response = await client.get(f"/games/{game_id}/world-entries")
        assert response.status_code == 200
        assert "World Entries" in response.text

    async def test_page_requires_membership(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client, db)
        await _login(client, 2)
        response = await client.get(f"/games/{game_id}/world-entries")
        assert response.status_code == 403

    async def test_page_blocked_during_setup(self, client: AsyncClient) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        response = await client.get(f"/games/{game_id}/world-entries")
        assert response.status_code == 403

    async def test_page_shows_add_form_for_active_game(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await self._setup(client, db)
        response = await client.get(f"/games/{game_id}/world-entries")
        assert response.status_code == 200
        assert "Add Entry" in response.text


class TestCreateWorldEntry:
    async def _setup(self, client: AsyncClient, db: AsyncSession) -> int:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        return game_id

    async def test_create_entry(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client, db)
        response = await client.post(
            f"/games/{game_id}/world-entries",
            data={
                "name": "The Old Mill",
                "entry_type": "location",
                "description": "A crumbling mill on the river.",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == f"/games/{game_id}/world-entries"

        entries = await _get_entries(db, game_id)
        assert len(entries) == 1
        assert entries[0].name == "The Old Mill"
        assert entries[0].entry_type == WorldEntryType.location
        assert entries[0].description == "A crumbling mill on the river."
        assert entries[0].game_id == game_id

    async def test_create_entry_requires_name(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client, db)
        response = await client.post(
            f"/games/{game_id}/world-entries",
            data={"name": "   ", "entry_type": "location", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_create_entry_requires_valid_type(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await self._setup(client, db)
        response = await client.post(
            f"/games/{game_id}/world-entries",
            data={"name": "Somewhere", "entry_type": "invalid_type", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_any_member_can_create_entry(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client, db)
        await _add_member(db, game_id, 2)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/world-entries",
            data={"name": "The Guild Hall", "entry_type": "faction", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 303
        entries = await _get_entries(db, game_id)
        assert any(e.name == "The Guild Hall" for e in entries)

    async def test_non_member_cannot_create_entry(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id = await self._setup(client, db)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/world-entries",
            data={"name": "Intruder Entry", "entry_type": "location", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_all_entry_types_accepted(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id = await self._setup(client, db)
        for t in ("location", "faction", "item", "concept", "other"):
            response = await client.post(
                f"/games/{game_id}/world-entries",
                data={"name": f"Entry {t}", "entry_type": t, "description": ""},
                follow_redirects=False,
            )
            assert response.status_code == 303, f"Type {t!r} should be accepted"


class TestEditWorldEntry:
    async def _setup_with_entry(self, client: AsyncClient, db: AsyncSession) -> tuple[int, int]:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        db.add(
            WorldEntry(
                game_id=game_id,
                entry_type=WorldEntryType.location,
                name="OldName",
                description="Old desc",
            )
        )
        await db.commit()
        entries = await _get_entries(db, game_id)
        return game_id, entries[0].id

    async def test_edit_page_loads(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, entry_id = await self._setup_with_entry(client, db)
        response = await client.get(f"/games/{game_id}/world-entries/{entry_id}/edit")
        assert response.status_code == 200
        assert "OldName" in response.text

    async def test_update_entry(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, entry_id = await self._setup_with_entry(client, db)
        response = await client.post(
            f"/games/{game_id}/world-entries/{entry_id}/edit",
            data={"name": "NewName", "entry_type": "faction", "description": "New desc"},
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        result = await db.execute(select(WorldEntry).where(WorldEntry.id == entry_id))
        entry = result.scalar_one()
        assert entry.name == "NewName"
        assert entry.entry_type == WorldEntryType.faction
        assert entry.description == "New desc"

    async def test_any_member_can_edit_entry(self, client: AsyncClient, db: AsyncSession) -> None:
        game_id, entry_id = await self._setup_with_entry(client, db)
        await _add_member(db, game_id, 2)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/world-entries/{entry_id}/edit",
            data={"name": "EditedByBob", "entry_type": "location", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        result = await db.execute(select(WorldEntry).where(WorldEntry.id == entry_id))
        entry = result.scalar_one()
        assert entry.name == "EditedByBob"

    async def test_non_member_cannot_edit_entry(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        game_id, entry_id = await self._setup_with_entry(client, db)
        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/world-entries/{entry_id}/edit",
            data={"name": "Hack", "entry_type": "location", "description": ""},
            follow_redirects=False,
        )
        assert response.status_code == 403


class TestWorldEntryNotifications:
    async def test_create_entry_sends_notification(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        """Creating an entry notifies other members."""
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        await _add_member(db, game_id, 2)

        response = await client.post(
            f"/games/{game_id}/world-entries",
            data={
                "name": "The Spire",
                "entry_type": "location",
                "description": "A tall tower.",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        result = await db.execute(
            select(Notification)
            .where(Notification.game_id == game_id)
            .where(Notification.notification_type == NotificationType.world_entry_created)
        )
        notifications = list(result.scalars().all())
        # Should notify Bob (user 2) but not Alice (creator)
        assert len(notifications) == 1
        assert notifications[0].user_id == 2
        assert "The Spire" in notifications[0].message

    async def test_create_entry_no_notification_to_creator(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        """The entry creator does not receive their own notification."""
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)

        await client.post(
            f"/games/{game_id}/world-entries",
            data={"name": "Solo Entry", "entry_type": "concept", "description": ""},
            follow_redirects=False,
        )

        db.expire_all()
        result = await db.execute(
            select(Notification)
            .where(Notification.game_id == game_id)
            .where(Notification.notification_type == NotificationType.world_entry_created)
            .where(Notification.user_id == 1)
        )
        notifications = list(result.scalars().all())
        assert len(notifications) == 0
