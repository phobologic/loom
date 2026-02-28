"""World entry creation and management routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.ai.client import suggest_world_entries as _ai_suggest_world_entries
from loom.database import AsyncSessionLocal, get_db
from loom.dependencies import get_current_user
from loom.models import (
    Beat,
    EventType,
    Game,
    GameMember,
    GameStatus,
    NotificationType,
    User,
    WorldEntry,
    WorldEntrySuggestion,
    WorldEntrySuggestionStatus,
    WorldEntryType,
)
from loom.notifications import notify_game_members
from loom.rendering import templates

logger = logging.getLogger(__name__)

router = APIRouter()


def _find_membership(game: Game, user_id: int) -> GameMember | None:
    """Return the GameMember record for user_id in game, or None."""
    for m in game.members:
        if m.user_id == user_id:
            return m
    return None


def _find_entry(game: Game, entry_id: int) -> WorldEntry | None:
    """Return the WorldEntry with entry_id in game, or None."""
    for e in game.world_entries:
        if e.id == entry_id:
            return e
    return None


def _find_suggestion(game: Game, suggestion_id: int) -> WorldEntrySuggestion | None:
    """Return the pending WorldEntrySuggestion with suggestion_id in game, or None."""
    for s in game.world_entry_suggestions:
        if s.id == suggestion_id and s.status == WorldEntrySuggestionStatus.pending:
            return s
    return None


async def _load_game_with_entries(game_id: int, db: AsyncSession) -> Game | None:
    """Load a game with members, world entries, and pending suggestions eager-loaded."""
    result = await db.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(
            selectinload(Game.members),
            selectinload(Game.world_entries),
            selectinload(Game.world_entry_suggestions),
        )
    )
    return result.scalar_one_or_none()


async def _scan_beat_for_world_entries(beat_id: int, game_id: int) -> None:
    """Background task: ask the AI if a newly-canon beat introduces new world elements.

    Creates WorldEntrySuggestion rows for any new elements found and notifies
    game members. AI failures never propagate — beat canonisation is never
    rolled back by this function.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Load beat with narrative events
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

            # Load game with world document and existing entries
            game_result = await db.execute(
                select(Game)
                .where(Game.id == game_id)
                .options(
                    selectinload(Game.members),
                    selectinload(Game.world_entries),
                    selectinload(Game.world_document),
                )
            )
            game = game_result.scalar_one_or_none()
            if game is None:
                return

            suggestions = await _ai_suggest_world_entries(
                narrative_text,
                game.world_entries,
                game=game,
                db=db,
                game_id=game_id,
            )
        except Exception:
            logger.exception("Failed to generate world entry suggestions for beat %d", beat_id)
            return

        if not suggestions:
            await db.commit()
            return

        for entry_type_str, name, description, reason in suggestions:
            try:
                entry_type = WorldEntryType(entry_type_str)
            except ValueError:
                continue
            name = name.strip()[:150]
            if not name:
                continue
            db.add(
                WorldEntrySuggestion(
                    game_id=game_id,
                    beat_id=beat_id,
                    suggested_type=entry_type,
                    suggested_name=name,
                    suggested_description=description.strip() or None,
                    reason=reason,
                    status=WorldEntrySuggestionStatus.pending,
                )
            )

        await db.flush()

        await notify_game_members(
            db,
            game,
            NotificationType.world_entry_suggested,
            "The AI spotted new world elements worth tracking",
            link=f"/games/{game_id}/world-entries",
        )
        await db.commit()


@router.get("/games/{game_id}/world-entries", response_class=HTMLResponse)
async def world_entries_page(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show world entry list, pending AI suggestions, and creation form."""
    game = await _load_game_with_entries(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status == GameStatus.setup:
        raise HTTPException(
            status_code=403,
            detail="World entry tracking is not available until Session 0 is complete",
        )

    pending_suggestions = [
        s for s in game.world_entry_suggestions if s.status == WorldEntrySuggestionStatus.pending
    ]

    return templates.TemplateResponse(
        request,
        "world_entries.html",
        {
            "game": game,
            "current_member": current_member,
            "current_user": current_user,
            "entries": game.world_entries,
            "entry_types": list(WorldEntryType),
            "editing": None,
            "pending_suggestions": pending_suggestions,
        },
    )


@router.post("/games/{game_id}/world-entries", response_class=RedirectResponse)
async def create_world_entry(
    game_id: int,
    request: Request,
    name: str = Form(...),
    entry_type: str = Form(...),
    description: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Create a new world entry accessible to all game members."""
    game = await _load_game_with_entries(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status not in (GameStatus.active, GameStatus.paused):
        raise HTTPException(status_code=403, detail="World entry creation requires an active game")

    try:
        parsed_type = WorldEntryType(entry_type)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid entry type: {entry_type!r}")

    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Entry name cannot be empty")
    if len(name) > 150:
        raise HTTPException(status_code=422, detail="Entry name cannot exceed 150 characters")

    entry = WorldEntry(
        game_id=game_id,
        entry_type=parsed_type,
        name=name,
        description=description.strip() or None,
    )
    db.add(entry)
    await db.flush()

    await notify_game_members(
        db,
        game,
        NotificationType.world_entry_created,
        f"{current_user.display_name} added {parsed_type.value}: {name}",
        link=f"/games/{game_id}/world-entries",
        exclude_user_id=current_user.id,
    )
    await db.commit()

    return RedirectResponse(url=f"/games/{game_id}/world-entries", status_code=303)


@router.post(
    "/games/{game_id}/world-entry-suggestions/{suggestion_id}/accept",
    response_class=RedirectResponse,
)
async def accept_world_entry_suggestion(
    game_id: int,
    suggestion_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Accept an AI suggestion: create the world entry and mark suggestion accepted."""
    game = await _load_game_with_entries(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status not in (GameStatus.active, GameStatus.paused):
        raise HTTPException(status_code=403, detail="Game must be active to accept suggestions")

    suggestion = _find_suggestion(game, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Suggestion not found or already resolved")

    entry = WorldEntry(
        game_id=game_id,
        entry_type=suggestion.suggested_type,
        name=suggestion.suggested_name,
        description=suggestion.suggested_description,
    )
    db.add(entry)
    suggestion.status = WorldEntrySuggestionStatus.accepted
    await db.flush()

    await notify_game_members(
        db,
        game,
        NotificationType.world_entry_created,
        f"{current_user.display_name} added {suggestion.suggested_type.value}: {suggestion.suggested_name}",
        link=f"/games/{game_id}/world-entries",
        exclude_user_id=current_user.id,
    )
    await db.commit()

    return RedirectResponse(url=f"/games/{game_id}/world-entries", status_code=303)


@router.post(
    "/games/{game_id}/world-entry-suggestions/{suggestion_id}/dismiss",
    response_class=RedirectResponse,
)
async def dismiss_world_entry_suggestion(
    game_id: int,
    suggestion_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Dismiss an AI suggestion without creating an entry."""
    game = await _load_game_with_entries(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    suggestion = _find_suggestion(game, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Suggestion not found or already resolved")

    suggestion.status = WorldEntrySuggestionStatus.dismissed
    await db.commit()

    return RedirectResponse(url=f"/games/{game_id}/world-entries", status_code=303)


@router.get("/games/{game_id}/world-entries/{entry_id}/edit", response_class=HTMLResponse)
async def edit_world_entry_page(
    game_id: int,
    entry_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the edit form for a world entry."""
    game = await _load_game_with_entries(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status == GameStatus.setup:
        raise HTTPException(
            status_code=403,
            detail="World entry tracking is not available until Session 0 is complete",
        )

    entry = _find_entry(game, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="World entry not found")

    pending_suggestions = [
        s for s in game.world_entry_suggestions if s.status == WorldEntrySuggestionStatus.pending
    ]

    return templates.TemplateResponse(
        request,
        "world_entries.html",
        {
            "game": game,
            "current_member": current_member,
            "current_user": current_user,
            "entries": game.world_entries,
            "entry_types": list(WorldEntryType),
            "editing": entry,
            "pending_suggestions": pending_suggestions,
        },
    )


@router.post("/games/{game_id}/world-entries/{entry_id}/edit", response_class=RedirectResponse)
async def update_world_entry(
    game_id: int,
    entry_id: int,
    request: Request,
    name: str = Form(...),
    entry_type: str = Form(...),
    description: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Update a world entry's fields. Any game member may edit any entry."""
    game = await _load_game_with_entries(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status == GameStatus.archived:
        raise HTTPException(status_code=403, detail="Cannot edit world entries in an archived game")

    entry = _find_entry(game, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="World entry not found")

    try:
        parsed_type = WorldEntryType(entry_type)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid entry type: {entry_type!r}")

    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Entry name cannot be empty")
    if len(name) > 150:
        raise HTTPException(status_code=422, detail="Entry name cannot exceed 150 characters")

    entry.name = name
    entry.entry_type = parsed_type
    entry.description = description.strip() or None
    await db.commit()

    return RedirectResponse(url=f"/games/{game_id}/world-entries", status_code=303)
