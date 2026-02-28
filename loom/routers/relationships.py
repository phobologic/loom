"""Relationship creation, management, and AI suggestion routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.ai.client import suggest_relationships as _ai_suggest_relationships
from loom.database import AsyncSessionLocal, get_db
from loom.dependencies import get_current_user
from loom.models import (
    Beat,
    EntityType,
    EventType,
    Game,
    GameMember,
    GameStatus,
    NotificationType,
    Relationship,
    RelationshipSuggestion,
    RelationshipSuggestionStatus,
    User,
)
from loom.notifications import notify_game_members
from loom.rendering import templates

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_ENTITY_TYPES = {e.value for e in EntityType}
_MAX_LABEL_LEN = 100


def _find_membership(game: Game, user_id: int) -> GameMember | None:
    """Return the GameMember record for user_id in game, or None."""
    for m in game.members:
        if m.user_id == user_id:
            return m
    return None


def _find_relationship(game: Game, rel_id: int) -> Relationship | None:
    """Return the Relationship with rel_id in game, or None."""
    for r in game.relationships:
        if r.id == rel_id:
            return r
    return None


def _find_suggestion(game: Game, sug_id: int) -> RelationshipSuggestion | None:
    """Return a pending RelationshipSuggestion with sug_id in game, or None."""
    for s in game.relationship_suggestions:
        if s.id == sug_id and s.status == RelationshipSuggestionStatus.pending:
            return s
    return None


async def _load_game_with_relationships(game_id: int, db: AsyncSession) -> Game | None:
    """Load a game with members, characters, NPCs, world entries, and relationships."""
    result = await db.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(
            selectinload(Game.members),
            selectinload(Game.characters),
            selectinload(Game.npcs),
            selectinload(Game.world_entries),
            selectinload(Game.relationships),
            selectinload(Game.relationship_suggestions),
        )
    )
    return result.scalar_one_or_none()


def _entity_display_name(
    game: Game,
    entity_type: str,
    entity_id: int,
) -> str:
    """Resolve a (type, id) pair to a human-readable name for template display."""
    if entity_type == EntityType.character.value:
        for c in game.characters:
            if c.id == entity_id:
                return c.name
    elif entity_type == EntityType.npc.value:
        for n in game.npcs:
            if n.id == entity_id:
                return n.name
    elif entity_type == EntityType.world_entry.value:
        for e in game.world_entries:
            if e.id == entity_id:
                return e.name
    return f"Unknown ({entity_type}:{entity_id})"


def _validate_entity_exists(game: Game, entity_type: str, entity_id: int) -> bool:
    """Return True if (entity_type, entity_id) refers to a tracked entity in game."""
    if entity_type == EntityType.character.value:
        return any(c.id == entity_id for c in game.characters)
    if entity_type == EntityType.npc.value:
        return any(n.id == entity_id for n in game.npcs)
    if entity_type == EntityType.world_entry.value:
        return any(e.id == entity_id for e in game.world_entries)
    return False


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------


async def _scan_beat_for_relationships(beat_id: int, game_id: int) -> None:
    """Background task: ask the AI if a newly-canon beat establishes new relationships.

    Creates RelationshipSuggestion rows and notifies game members.
    AI failures never propagate — beat canonisation is never rolled back.
    """
    async with AsyncSessionLocal() as db:
        try:
            beat_result = await db.execute(
                select(Beat).where(Beat.id == beat_id).options(selectinload(Beat.events))
            )
            beat = beat_result.scalar_one_or_none()
            if beat is None:
                return

            narrative_text = " ".join(
                e.content for e in beat.events if e.type == EventType.narrative and e.content
            ).strip()
            if not narrative_text:
                return

            game_result = await db.execute(
                select(Game)
                .where(Game.id == game_id)
                .options(
                    selectinload(Game.members),
                    selectinload(Game.characters),
                    selectinload(Game.npcs),
                    selectinload(Game.world_entries),
                    selectinload(Game.relationships),
                    selectinload(Game.world_document),
                )
            )
            game = game_result.scalar_one_or_none()
            if game is None:
                return

            # Skip if there are fewer than 2 tracked entities — nothing to relate
            total_entities = len(game.characters) + len(game.npcs) + len(game.world_entries)
            if total_entities < 2:
                return

            existing = [
                (
                    r.entity_a_type.value,
                    r.entity_a_id,
                    r.entity_b_type.value,
                    r.entity_b_id,
                    r.label,
                )
                for r in game.relationships
            ]

            suggestions = await _ai_suggest_relationships(
                narrative_text,
                game.characters,
                game.npcs,
                game.world_entries,
                existing,
                game=game,
                db=db,
                game_id=game_id,
            )
        except Exception:
            logger.exception("Failed to generate relationship suggestions for beat %d", beat_id)
            return

        if not suggestions:
            await db.commit()
            return

        added = 0
        valid_char_ids = {c.id for c in game.characters}
        valid_npc_ids = {n.id for n in game.npcs}
        valid_we_ids = {e.id for e in game.world_entries}

        for a_type, a_id, b_type, b_id, label, reason in suggestions:
            # Validate entity types
            if a_type not in _VALID_ENTITY_TYPES or b_type not in _VALID_ENTITY_TYPES:
                continue

            # Validate IDs against tracked entities
            def _id_valid(etype: str, eid: int) -> bool:
                if etype == "character":
                    return eid in valid_char_ids
                if etype == "npc":
                    return eid in valid_npc_ids
                if etype == "world_entry":
                    return eid in valid_we_ids
                return False

            if not _id_valid(a_type, a_id) or not _id_valid(b_type, b_id):
                continue
            if a_type == b_type and a_id == b_id:
                continue

            label = label.strip()[:_MAX_LABEL_LEN]
            if not label:
                continue

            db.add(
                RelationshipSuggestion(
                    game_id=game_id,
                    beat_id=beat_id,
                    entity_a_type=EntityType(a_type),
                    entity_a_id=a_id,
                    entity_b_type=EntityType(b_type),
                    entity_b_id=b_id,
                    suggested_label=label,
                    reason=reason,
                    status=RelationshipSuggestionStatus.pending,
                )
            )
            added += 1

        if added == 0:
            await db.commit()
            return

        await db.flush()
        await notify_game_members(
            db,
            game,
            NotificationType.relationship_suggested,
            "The AI spotted new relationships worth tracking",
            link=f"/games/{game_id}/relationships",
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/games/{game_id}/relationships", response_class=HTMLResponse)
async def relationships_page(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show relationship list, pending AI suggestions, and creation form."""
    game = await _load_game_with_relationships(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status == GameStatus.setup:
        raise HTTPException(
            status_code=403,
            detail="Relationship tracking is not available until Session 0 is complete",
        )

    pending_suggestions = [
        s for s in game.relationship_suggestions if s.status == RelationshipSuggestionStatus.pending
    ]

    # Enrich relationships and suggestions with display names for the template
    enriched_rels = [
        {
            "rel": r,
            "name_a": _entity_display_name(game, r.entity_a_type.value, r.entity_a_id),
            "name_b": _entity_display_name(game, r.entity_b_type.value, r.entity_b_id),
        }
        for r in game.relationships
    ]
    enriched_suggestions = [
        {
            "sug": s,
            "name_a": _entity_display_name(game, s.entity_a_type.value, s.entity_a_id),
            "name_b": _entity_display_name(game, s.entity_b_type.value, s.entity_b_id),
        }
        for s in pending_suggestions
    ]

    return templates.TemplateResponse(
        request,
        "relationships.html",
        {
            "game": game,
            "current_member": current_member,
            "current_user": current_user,
            "enriched_rels": enriched_rels,
            "enriched_suggestions": enriched_suggestions,
            "entity_types": list(EntityType),
        },
    )


@router.post("/games/{game_id}/relationships", response_class=RedirectResponse)
async def create_relationship(
    game_id: int,
    entity_a_type: str = Form(...),
    entity_a_id: int = Form(...),
    label: str = Form(...),
    entity_b_type: str = Form(...),
    entity_b_id: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Create a new relationship between two tracked entities."""
    game = await _load_game_with_relationships(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status not in (GameStatus.active, GameStatus.paused):
        raise HTTPException(status_code=403, detail="Relationship creation requires an active game")

    if entity_a_type not in _VALID_ENTITY_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid entity type: {entity_a_type!r}")
    if entity_b_type not in _VALID_ENTITY_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid entity type: {entity_b_type!r}")

    if not _validate_entity_exists(game, entity_a_type, entity_a_id):
        raise HTTPException(status_code=422, detail="First entity not found in this game")
    if not _validate_entity_exists(game, entity_b_type, entity_b_id):
        raise HTTPException(status_code=422, detail="Second entity not found in this game")

    if entity_a_type == entity_b_type and entity_a_id == entity_b_id:
        raise HTTPException(
            status_code=422, detail="A relationship must be between two different entities"
        )

    label = label.strip()
    if not label:
        raise HTTPException(status_code=422, detail="Relationship label cannot be empty")
    if len(label) > _MAX_LABEL_LEN:
        raise HTTPException(
            status_code=422,
            detail=f"Relationship label cannot exceed {_MAX_LABEL_LEN} characters",
        )

    rel = Relationship(
        game_id=game_id,
        entity_a_type=EntityType(entity_a_type),
        entity_a_id=entity_a_id,
        entity_b_type=EntityType(entity_b_type),
        entity_b_id=entity_b_id,
        label=label,
        created_by_id=current_user.id,
    )
    db.add(rel)
    await db.flush()

    name_a = _entity_display_name(game, entity_a_type, entity_a_id)
    name_b = _entity_display_name(game, entity_b_type, entity_b_id)
    await notify_game_members(
        db,
        game,
        NotificationType.relationship_created,
        f"{current_user.display_name} added relationship: {name_a} — {label} — {name_b}",
        link=f"/games/{game_id}/relationships",
        exclude_user_id=current_user.id,
    )
    await db.commit()

    return RedirectResponse(url=f"/games/{game_id}/relationships", status_code=303)


@router.post(
    "/games/{game_id}/relationships/{rel_id}/delete",
    response_class=RedirectResponse,
)
async def delete_relationship(
    game_id: int,
    rel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Delete a relationship. Any game member may delete any relationship."""
    game = await _load_game_with_relationships(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status == GameStatus.archived:
        raise HTTPException(
            status_code=403, detail="Cannot delete relationships in an archived game"
        )

    rel = _find_relationship(game, rel_id)
    if rel is None:
        raise HTTPException(status_code=404, detail="Relationship not found")

    await db.delete(rel)
    await db.commit()

    return RedirectResponse(url=f"/games/{game_id}/relationships", status_code=303)


@router.post(
    "/games/{game_id}/relationship-suggestions/{sug_id}/accept",
    response_class=RedirectResponse,
)
async def accept_relationship_suggestion(
    game_id: int,
    sug_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Accept an AI-suggested relationship: create the relationship and mark suggestion accepted."""
    game = await _load_game_with_relationships(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status not in (GameStatus.active, GameStatus.paused):
        raise HTTPException(status_code=403, detail="Game must be active to accept suggestions")

    sug = _find_suggestion(game, sug_id)
    if sug is None:
        raise HTTPException(status_code=404, detail="Suggestion not found or already resolved")

    rel = Relationship(
        game_id=game_id,
        entity_a_type=sug.entity_a_type,
        entity_a_id=sug.entity_a_id,
        entity_b_type=sug.entity_b_type,
        entity_b_id=sug.entity_b_id,
        label=sug.suggested_label,
        created_by_id=current_user.id,
    )
    db.add(rel)
    sug.status = RelationshipSuggestionStatus.accepted
    await db.flush()

    name_a = _entity_display_name(game, sug.entity_a_type.value, sug.entity_a_id)
    name_b = _entity_display_name(game, sug.entity_b_type.value, sug.entity_b_id)
    await notify_game_members(
        db,
        game,
        NotificationType.relationship_created,
        f"{current_user.display_name} added relationship: {name_a} — {sug.suggested_label} — {name_b}",
        link=f"/games/{game_id}/relationships",
        exclude_user_id=current_user.id,
    )
    await db.commit()

    return RedirectResponse(url=f"/games/{game_id}/relationships", status_code=303)


@router.post(
    "/games/{game_id}/relationship-suggestions/{sug_id}/dismiss",
    response_class=RedirectResponse,
)
async def dismiss_relationship_suggestion(
    game_id: int,
    sug_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Dismiss an AI-suggested relationship without creating it."""
    game = await _load_game_with_relationships(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    sug = _find_suggestion(game, sug_id)
    if sug is None:
        raise HTTPException(status_code=404, detail="Suggestion not found or already resolved")

    sug.status = RelationshipSuggestionStatus.dismissed
    await db.commit()

    return RedirectResponse(url=f"/games/{game_id}/relationships", status_code=303)
