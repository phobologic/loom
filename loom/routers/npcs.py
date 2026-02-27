"""NPC creation and management routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.ai.client import suggest_npc_details
from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import (
    NPC,
    Beat,
    EventType,
    Game,
    GameMember,
    GameStatus,
    NotificationType,
    User,
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

    npc = NPC(
        game_id=game_id,
        name=name,
        description=description.strip() or None,
        notes=notes.strip() or None,
    )
    db.add(npc)
    await db.flush()

    await notify_game_members(
        db,
        game,
        NotificationType.npc_created,
        f"{current_user.display_name} added NPC: {name}",
        link=f"/games/{game_id}/npcs",
        exclude_user_id=current_user.id,
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


async def _load_beat_for_npc(
    beat_id: int, db: AsyncSession
) -> tuple[Beat, Game] | tuple[None, None]:
    """Load a beat with events and its parent game (with members, npcs, characters, world doc).

    Uses two queries: first the beat to get scene_id, then derives game_id from a
    scene→act join, and finally loads the game with all needed relationships.
    """
    from loom.models import Act, Scene

    beat_result = await db.execute(
        select(Beat).where(Beat.id == beat_id).options(selectinload(Beat.events))
    )
    beat = beat_result.scalar_one_or_none()
    if beat is None:
        return None, None

    # Resolve game_id through scene → act
    game_id_result = await db.execute(
        select(Act.game_id).join(Scene, Scene.act_id == Act.id).where(Scene.id == beat.scene_id)
    )
    game_id_val = game_id_result.scalar_one_or_none()
    if game_id_val is None:
        return None, None

    game_result = await db.execute(
        select(Game)
        .where(Game.id == game_id_val)
        .options(
            selectinload(Game.members),
            selectinload(Game.npcs),
            selectinload(Game.characters),
            selectinload(Game.world_document),
        )
    )
    game = game_result.scalar_one_or_none()
    return beat, game


@router.get("/games/{game_id}/beats/{beat_id}/npc/new", response_class=HTMLResponse)
async def npc_from_beat_page(
    game_id: int,
    beat_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the NPC creation form anchored to a specific beat."""
    beat, game = await _load_beat_for_npc(beat_id, db)
    if beat is None or game is None:
        raise HTTPException(status_code=404, detail="Beat not found")
    if game.id != game_id:
        raise HTTPException(status_code=404, detail="Beat not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status not in (GameStatus.active, GameStatus.paused):
        raise HTTPException(status_code=403, detail="NPC creation requires an active game")

    beat_text = " ".join(
        e.content for e in beat.events if e.type == EventType.narrative and e.content
    )

    return templates.TemplateResponse(
        request,
        "npc_from_beat.html",
        {
            "game": game,
            "beat": beat,
            "beat_text": beat_text,
            "current_user": current_user,
        },
    )


@router.post("/games/{game_id}/beats/{beat_id}/npc/suggest", response_class=HTMLResponse)
async def npc_suggest(
    game_id: int,
    beat_id: int,
    request: Request,
    description: str = Form(...),
    name: str = Form(""),
    notes: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Generate AI name/want suggestions for a new NPC (HTMX endpoint)."""
    beat, game = await _load_beat_for_npc(beat_id, db)
    if beat is None or game is None:
        raise HTTPException(status_code=404, detail="Beat not found")
    if game.id != game_id:
        raise HTTPException(status_code=404, detail="Beat not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status not in (GameStatus.active, GameStatus.paused):
        raise HTTPException(status_code=403, detail="NPC creation requires an active game")

    beat_text = " ".join(
        e.content for e in beat.events if e.type == EventType.narrative and e.content
    )

    existing_pc_names = [c.name for c in game.characters if c.owner_id is not None]
    existing_npc_names = [n.name for n in game.npcs]

    name_suggestions: list[str] = []
    want_suggestions: list[str] = []
    try:
        name_suggestions, want_suggestions = await suggest_npc_details(
            beat_text=beat_text,
            role=description.strip(),
            name=name.strip() or None,
            want=notes.strip() or None,
            existing_pc_names=existing_pc_names,
            existing_npc_names=existing_npc_names,
            game=game,
            db=db,
            game_id=game_id,
        )
        await db.commit()
    except Exception:
        logger.exception("Failed to generate NPC suggestions for beat %d", beat_id)

    return templates.TemplateResponse(
        request,
        "partials/npc_suggestions.html",
        {
            "name_suggestions": name_suggestions,
            "want_suggestions": want_suggestions,
        },
    )
