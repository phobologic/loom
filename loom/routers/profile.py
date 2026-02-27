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
from loom.models import EmailPref, GameMember, User
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
    email_pref: str = Form(default="digest"),
    prose_mode: str = Form(default="always"),
    prose_threshold_words: int = Form(default=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Update display name and notification preference."""
    display_name = display_name.strip()[:100]
    if display_name:
        current_user.display_name = display_name
    current_user.notify_enabled = notify_enabled
    if email_pref in {p.value for p in EmailPref}:
        current_user.email_pref = EmailPref(email_pref)
    if prose_mode in ("always", "never", "threshold"):
        current_user.prose_mode = prose_mode
    current_user.prose_threshold_words = max(1, prose_threshold_words)
    await db.commit()
    return RedirectResponse(url="/profile", status_code=303)
