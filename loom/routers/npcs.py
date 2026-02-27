"""NPC creation and management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import (
    NPC,
    Game,
    GameMember,
    GameStatus,
    User,
)
from loom.rendering import templates

router = APIRouter()


def _find_membership(game: Game, user_id: int) -> GameMember | None:
    """Return the GameMember record for user_id in game, or None."""
    for m in game.members:
        if m.user_id == user_id:
            return m
    return None


def _find_npc(game: Game, npc_id: int) -> NPC | None:
    """Return the NPC with npc_id in game, or None."""
    for n in game.npcs:
        if n.id == npc_id:
            return n
    return None


async def _load_game_with_npcs(game_id: int, db: AsyncSession) -> Game | None:
    """Load a game with members and NPCs eager-loaded."""
    result = await db.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(
            selectinload(Game.members),
            selectinload(Game.npcs),
        )
    )
    return result.scalar_one_or_none()


@router.get("/games/{game_id}/npcs", response_class=HTMLResponse)
async def npcs_page(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show NPC list and creation form."""
    game = await _load_game_with_npcs(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status == GameStatus.setup:
        raise HTTPException(
            status_code=403,
            detail="NPC tracking is not available until Session 0 is complete",
        )

    return templates.TemplateResponse(
        request,
        "npcs.html",
        {
            "game": game,
            "current_member": current_member,
            "current_user": current_user,
            "npcs": game.npcs,
            "editing": None,
        },
    )


@router.post("/games/{game_id}/npcs", response_class=RedirectResponse)
async def create_npc(
    game_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    notes: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Create a new NPC accessible to all game members."""
    game = await _load_game_with_npcs(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status not in (GameStatus.active, GameStatus.paused):
        raise HTTPException(status_code=403, detail="NPC creation requires an active game")

    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="NPC name cannot be empty")
    if len(name) > 100:
        raise HTTPException(status_code=422, detail="NPC name cannot exceed 100 characters")

    db.add(
        NPC(
            game_id=game_id,
            name=name,
            description=description.strip() or None,
            notes=notes.strip() or None,
        )
    )
    await db.commit()

    return RedirectResponse(url=f"/games/{game_id}/npcs", status_code=303)


@router.get("/games/{game_id}/npcs/{npc_id}/edit", response_class=HTMLResponse)
async def edit_npc_page(
    game_id: int,
    npc_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the edit form for an NPC."""
    game = await _load_game_with_npcs(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    npc = _find_npc(game, npc_id)
    if npc is None:
        raise HTTPException(status_code=404, detail="NPC not found")

    return templates.TemplateResponse(
        request,
        "npcs.html",
        {
            "game": game,
            "current_member": current_member,
            "current_user": current_user,
            "npcs": game.npcs,
            "editing": npc,
        },
    )


@router.post("/games/{game_id}/npcs/{npc_id}/edit", response_class=RedirectResponse)
async def update_npc(
    game_id: int,
    npc_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    notes: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Update an NPC's fields. Any game member may edit any NPC."""
    game = await _load_game_with_npcs(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status == GameStatus.archived:
        raise HTTPException(status_code=403, detail="Cannot edit NPCs in an archived game")

    npc = _find_npc(game, npc_id)
    if npc is None:
        raise HTTPException(status_code=404, detail="NPC not found")

    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="NPC name cannot be empty")
    if len(name) > 100:
        raise HTTPException(status_code=422, detail="NPC name cannot exceed 100 characters")

    npc.name = name
    npc.description = description.strip() or None
    npc.notes = notes.strip() or None
    await db.commit()

    return RedirectResponse(url=f"/games/{game_id}/npcs", status_code=303)
