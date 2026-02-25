"""Safety tools (lines and veils) routes."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import Game, GameMember, GameSafetyTool, MemberRole, SafetyToolKind, User
from loom.rendering import templates

router = APIRouter()


def _safe_referer(request: Request, fallback: str) -> str:
    """Return the Referer URL only if it is same-origin; otherwise return fallback."""
    referer = request.headers.get("referer")
    if referer and urlparse(referer).netloc == request.url.netloc:
        return referer
    return fallback


def _find_membership(game: Game, user_id: int) -> GameMember | None:
    """Return the GameMember record for user_id in game, or None."""
    for m in game.members:
        if m.user_id == user_id:
            return m
    return None


async def _load_game_with_members(game_id: int, db: AsyncSession) -> Game | None:
    result = await db.execute(
        select(Game).where(Game.id == game_id).options(selectinload(Game.members))
    )
    return result.scalar_one_or_none()


async def _load_safety_tools(game_id: int, db: AsyncSession) -> list[GameSafetyTool]:
    result = await db.execute(
        select(GameSafetyTool)
        .where(GameSafetyTool.game_id == game_id)
        .options(selectinload(GameSafetyTool.user))
        .order_by(GameSafetyTool.created_at)
    )
    return list(result.scalars().all())


@router.get("/games/{game_id}/safety-tools", response_class=HTMLResponse)
async def safety_tools_page(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the safety tools management page for a game."""
    game = await _load_game_with_members(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    safety_tools = await _load_safety_tools(game_id, db)

    return templates.TemplateResponse(
        request,
        "safety_tools.html",
        {
            "game": game,
            "current_member": current_member,
            "current_user": current_user,
            "safety_tools": safety_tools,
        },
    )


@router.post("/games/{game_id}/safety-tools/add", response_class=RedirectResponse)
async def add_safety_tool(
    game_id: int,
    request: Request,
    kind: str = Form(...),
    description: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Add a new line or veil (any member)."""
    game = await _load_game_with_members(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    try:
        kind_enum = SafetyToolKind(kind)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid kind; must be 'line' or 'veil'")

    description = description.strip()
    if not description:
        raise HTTPException(status_code=422, detail="Description cannot be empty")

    db.add(
        GameSafetyTool(
            game_id=game_id,
            user_id=current_user.id,
            kind=kind_enum,
            description=description,
        )
    )
    await db.commit()

    return RedirectResponse(
        url=_safe_referer(request, f"/games/{game_id}/safety-tools"), status_code=303
    )


@router.post("/games/{game_id}/safety-tools/{tool_id}/delete", response_class=RedirectResponse)
async def delete_safety_tool(
    game_id: int,
    tool_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Delete a line or veil. Any member can delete their own; organizer can delete any."""
    game = await _load_game_with_members(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    result = await db.execute(
        select(GameSafetyTool).where(
            GameSafetyTool.id == tool_id, GameSafetyTool.game_id == game_id
        )
    )
    tool = result.scalar_one_or_none()
    if tool is None:
        raise HTTPException(status_code=404, detail="Safety tool not found")

    is_own = tool.user_id == current_user.id
    is_organizer = current_member.role == MemberRole.organizer
    if not is_own and not is_organizer:
        raise HTTPException(status_code=403, detail="You can only delete your own entries")

    await db.delete(tool)
    await db.commit()

    return RedirectResponse(
        url=_safe_referer(request, f"/games/{game_id}/safety-tools"), status_code=303
    )
