"""Tests for relationship creation, management, and AI suggestion routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loom.models import (
    NPC,
    Character,
    EntityType,
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    Notification,
    NotificationType,
    Relationship,
    RelationshipSuggestion,
    RelationshipSuggestionStatus,
    WorldEntry,
    WorldEntryType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


async def _create_npc(db: AsyncSession, game_id: int, name: str = "Dock Master Venn") -> int:
    npc = NPC(game_id=game_id, name=name)
    db.add(npc)
    await db.commit()
    return npc.id


async def _create_character(
    db: AsyncSession, game_id: int, owner_id: int, name: str = "Kira"
) -> int:
    char = Character(game_id=game_id, owner_id=owner_id, name=name)
    db.add(char)
    await db.commit()
    return char.id


async def _create_world_entry(
    db: AsyncSession,
    game_id: int,
    name: str = "The Docks",
    entry_type: WorldEntryType = WorldEntryType.location,
) -> int:
    entry = WorldEntry(game_id=game_id, name=name, entry_type=entry_type)
    db.add(entry)
    await db.commit()
    return entry.id


async def _get_relationships(db: AsyncSession, game_id: int) -> list[Relationship]:
    result = await db.execute(select(Relationship).where(Relationship.game_id == game_id))
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRelationshipsPage:
    async def test_page_loads_for_member(self, client: AsyncClient, db: AsyncSession) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)

        response = await client.get(f"/games/{game_id}/relationships")
        assert response.status_code == 200
        assert "Relationships" in response.text

    async def test_page_forbidden_non_member(self, client: AsyncClient, db: AsyncSession) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)

        await _login(client, 2)  # not a member
        response = await client.get(f"/games/{game_id}/relationships")
        assert response.status_code == 403

    async def test_page_blocked_during_setup(self, client: AsyncClient, db: AsyncSession) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        # game is still in setup

        response = await client.get(f"/games/{game_id}/relationships")
        assert response.status_code == 403


class TestCreateRelationship:
    async def test_create_npc_to_npc(self, client: AsyncClient, db: AsyncSession) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)

        npc_a_id = await _create_npc(db, game_id, "Kira")
        npc_b_id = await _create_npc(db, game_id, "Venn")

        response = await client.post(
            f"/games/{game_id}/relationships",
            data={
                "entity_a_type": "npc",
                "entity_a_id": str(npc_a_id),
                "label": "rivals with",
                "entity_b_type": "npc",
                "entity_b_id": str(npc_b_id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        rels = await _get_relationships(db, game_id)
        assert len(rels) == 1
        rel = rels[0]
        assert rel.entity_a_type == EntityType.npc
        assert rel.entity_a_id == npc_a_id
        assert rel.label == "rivals with"
        assert rel.entity_b_type == EntityType.npc
        assert rel.entity_b_id == npc_b_id

    async def test_create_character_to_world_entry(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)

        char_id = await _create_character(db, game_id, owner_id=1)
        entry_id = await _create_world_entry(db, game_id)

        response = await client.post(
            f"/games/{game_id}/relationships",
            data={
                "entity_a_type": "character",
                "entity_a_id": str(char_id),
                "label": "based at",
                "entity_b_type": "world_entry",
                "entity_b_id": str(entry_id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        rels = await _get_relationships(db, game_id)
        assert len(rels) == 1
        assert rels[0].entity_a_type == EntityType.character
        assert rels[0].entity_b_type == EntityType.world_entry

    async def test_create_notifies_other_members(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        await _add_member(db, game_id, 2)

        npc_a_id = await _create_npc(db, game_id, "Kira")
        npc_b_id = await _create_npc(db, game_id, "Venn")

        await client.post(
            f"/games/{game_id}/relationships",
            data={
                "entity_a_type": "npc",
                "entity_a_id": str(npc_a_id),
                "label": "rivals with",
                "entity_b_type": "npc",
                "entity_b_id": str(npc_b_id),
            },
            follow_redirects=False,
        )

        db.expire_all()
        notif = await db.scalar(
            select(Notification).where(
                Notification.user_id == 2,
                Notification.notification_type == NotificationType.relationship_created,
            )
        )
        assert notif is not None

    async def test_reject_self_relationship(self, client: AsyncClient, db: AsyncSession) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        npc_id = await _create_npc(db, game_id)

        response = await client.post(
            f"/games/{game_id}/relationships",
            data={
                "entity_a_type": "npc",
                "entity_a_id": str(npc_id),
                "label": "knows",
                "entity_b_type": "npc",
                "entity_b_id": str(npc_id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_reject_empty_label(self, client: AsyncClient, db: AsyncSession) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        npc_a_id = await _create_npc(db, game_id, "A")
        npc_b_id = await _create_npc(db, game_id, "B")

        response = await client.post(
            f"/games/{game_id}/relationships",
            data={
                "entity_a_type": "npc",
                "entity_a_id": str(npc_a_id),
                "label": "   ",
                "entity_b_type": "npc",
                "entity_b_id": str(npc_b_id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_reject_entity_not_in_game(self, client: AsyncClient, db: AsyncSession) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        npc_id = await _create_npc(db, game_id)

        response = await client.post(
            f"/games/{game_id}/relationships",
            data={
                "entity_a_type": "npc",
                "entity_a_id": str(npc_id),
                "label": "knows",
                "entity_b_type": "npc",
                "entity_b_id": "99999",  # doesn't exist
            },
            follow_redirects=False,
        )
        assert response.status_code == 422

    async def test_non_member_cannot_create(self, client: AsyncClient, db: AsyncSession) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        npc_a_id = await _create_npc(db, game_id, "A")
        npc_b_id = await _create_npc(db, game_id, "B")

        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/relationships",
            data={
                "entity_a_type": "npc",
                "entity_a_id": str(npc_a_id),
                "label": "knows",
                "entity_b_type": "npc",
                "entity_b_id": str(npc_b_id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 403


class TestDeleteRelationship:
    async def test_delete_relationship(self, client: AsyncClient, db: AsyncSession) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        npc_a_id = await _create_npc(db, game_id, "A")
        npc_b_id = await _create_npc(db, game_id, "B")

        # Create then delete
        await client.post(
            f"/games/{game_id}/relationships",
            data={
                "entity_a_type": "npc",
                "entity_a_id": str(npc_a_id),
                "label": "rivals with",
                "entity_b_type": "npc",
                "entity_b_id": str(npc_b_id),
            },
            follow_redirects=False,
        )

        db.expire_all()
        rels = await _get_relationships(db, game_id)
        assert len(rels) == 1
        rel_id = rels[0].id

        response = await client.post(
            f"/games/{game_id}/relationships/{rel_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        assert await _get_relationships(db, game_id) == []

    async def test_non_member_cannot_delete(self, client: AsyncClient, db: AsyncSession) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        npc_a_id = await _create_npc(db, game_id, "A")
        npc_b_id = await _create_npc(db, game_id, "B")

        db.add(
            Relationship(
                game_id=game_id,
                entity_a_type=EntityType.npc,
                entity_a_id=npc_a_id,
                entity_b_type=EntityType.npc,
                entity_b_id=npc_b_id,
                label="rivals with",
                created_by_id=1,
            )
        )
        await db.commit()

        db.expire_all()
        rels = await _get_relationships(db, game_id)
        rel_id = rels[0].id

        await _login(client, 2)
        response = await client.post(
            f"/games/{game_id}/relationships/{rel_id}/delete",
            follow_redirects=False,
        )
        assert response.status_code == 403


class TestRelationshipSuggestions:
    async def _seed_suggestion(
        self,
        db: AsyncSession,
        game_id: int,
        npc_a_id: int,
        npc_b_id: int,
    ) -> int:
        sug = RelationshipSuggestion(
            game_id=game_id,
            entity_a_type=EntityType.npc,
            entity_a_id=npc_a_id,
            entity_b_type=EntityType.npc,
            entity_b_id=npc_b_id,
            suggested_label="rivals with",
            reason="They clashed in the dockside scene.",
            status=RelationshipSuggestionStatus.pending,
        )
        db.add(sug)
        await db.commit()
        return sug.id

    async def test_accept_creates_relationship(self, client: AsyncClient, db: AsyncSession) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        npc_a_id = await _create_npc(db, game_id, "Kira")
        npc_b_id = await _create_npc(db, game_id, "Venn")
        sug_id = await self._seed_suggestion(db, game_id, npc_a_id, npc_b_id)

        response = await client.post(
            f"/games/{game_id}/relationship-suggestions/{sug_id}/accept",
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        rels = await _get_relationships(db, game_id)
        assert len(rels) == 1
        assert rels[0].label == "rivals with"

        sug = await db.get(RelationshipSuggestion, sug_id)
        assert sug is not None
        assert sug.status == RelationshipSuggestionStatus.accepted

    async def test_dismiss_does_not_create_relationship(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        npc_a_id = await _create_npc(db, game_id, "Kira")
        npc_b_id = await _create_npc(db, game_id, "Venn")
        sug_id = await self._seed_suggestion(db, game_id, npc_a_id, npc_b_id)

        response = await client.post(
            f"/games/{game_id}/relationship-suggestions/{sug_id}/dismiss",
            follow_redirects=False,
        )
        assert response.status_code == 303

        db.expire_all()
        assert await _get_relationships(db, game_id) == []

        sug = await db.get(RelationshipSuggestion, sug_id)
        assert sug is not None
        assert sug.status == RelationshipSuggestionStatus.dismissed

    async def test_cannot_accept_twice(self, client: AsyncClient, db: AsyncSession) -> None:
        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)
        npc_a_id = await _create_npc(db, game_id, "Kira")
        npc_b_id = await _create_npc(db, game_id, "Venn")
        sug_id = await self._seed_suggestion(db, game_id, npc_a_id, npc_b_id)

        await client.post(
            f"/games/{game_id}/relationship-suggestions/{sug_id}/accept",
            follow_redirects=False,
        )
        # Accept again — suggestion no longer pending
        response = await client.post(
            f"/games/{game_id}/relationship-suggestions/{sug_id}/accept",
            follow_redirects=False,
        )
        assert response.status_code == 404


class TestScanBeatForRelationships:
    async def test_scan_with_no_entities_skips_ai(
        self, client: AsyncClient, db: AsyncSession, mock_ai, monkeypatch
    ) -> None:
        """Background scan should not call AI if there are fewer than 2 entities."""
        from loom.routers.relationships import _scan_beat_for_relationships

        called = []

        async def _fake_suggest(*args, **kwargs):
            called.append(True)
            return []

        monkeypatch.setattr("loom.routers.relationships._ai_suggest_relationships", _fake_suggest)

        await _login(client, 1)
        game_id = await _create_game(client)
        await _activate_game(db, game_id)

        # No entities — scan should return early
        await _scan_beat_for_relationships(beat_id=99999, game_id=game_id)
        assert called == []
