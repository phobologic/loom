"""User profile routes — display name, notification preferences, games list."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import GameMember, User
from loom.rendering import templates

router = APIRouter()


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the user's profile page."""
    result = await db.execute(
        select(User)
        .where(User.id == current_user.id)
        .options(
            selectinload(User.memberships).selectinload(GameMember.game),
        )
    )
    user = result.scalar_one()
    return templates.TemplateResponse(request, "profile.html", {"profile_user": user})


@router.post("/profile")
async def update_profile(
    request: Request,
    display_name: str = Form(...),
    notify_enabled: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Update display name and notification preference."""
    display_name = display_name.strip()[:100]
    if display_name:
        current_user.display_name = display_name
    current_user.notify_enabled = notify_enabled
    await db.commit()
    return RedirectResponse(url="/profile", status_code=303)
