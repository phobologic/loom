"""Games dashboard routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import Game, GameMember, User

templates = Jinja2Templates(directory="loom/templates")

router = APIRouter()


@router.get("/games", response_class=HTMLResponse)
async def my_games(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the current user's games dashboard."""
    result = await db.execute(
        select(Game)
        .join(GameMember, GameMember.game_id == Game.id)
        .where(GameMember.user_id == current_user.id)
        .order_by(Game.name)
    )
    games = result.scalars().all()
    return templates.TemplateResponse(request, "games.html", {"user": current_user, "games": games})
