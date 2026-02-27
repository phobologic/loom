"""World entry creation and management routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import (
    Game,
    GameMember,
    GameStatus,
    NotificationType,
    User,
    WorldEntry,
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


async def _load_game_with_entries(game_id: int, db: AsyncSession) -> Game | None:
    """Load a game with members and world entries eager-loaded."""
    result = await db.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(
            selectinload(Game.members),
            selectinload(Game.world_entries),
        )
    )
    return result.scalar_one_or_none()


@router.get("/games/{game_id}/world-entries", response_class=HTMLResponse)
async def world_entries_page(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show world entry list and creation form."""
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
