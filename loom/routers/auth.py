"""Dev-only authentication routes.

These routes are a placeholder for real OAuth (Step 25). They allow
developers to select any seeded test user to log in as.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from loom.database import get_db
from loom.models import User
from loom.rendering import templates

router = APIRouter()


@router.get("/dev/login", response_class=HTMLResponse)
async def dev_login_page(request: Request, db: AsyncSession = Depends(get_db)) -> HTMLResponse:
    """Show the dev login page with all seeded users."""
    result = await db.execute(select(User).order_by(User.display_name))
    users = result.scalars().all()
    return templates.TemplateResponse(request, "dev_login.html", {"users": users})


@router.post("/dev/login")
async def dev_login(
    request: Request,
    user_id: int = Form(...),
) -> RedirectResponse:
    """Set the session to the chosen user and redirect to /games."""
    request.session["user_id"] = user_id
    return RedirectResponse(url="/games", status_code=303)


@router.post("/dev/logout")
async def dev_logout(request: Request) -> RedirectResponse:
    """Clear the session and redirect to /dev/login."""
    request.session.clear()
    return RedirectResponse(url="/dev/login", status_code=303)
