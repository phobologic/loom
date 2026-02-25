"""FastAPI dependencies for Loom."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from loom.database import get_db
from loom.models import User


class _AuthRedirect(Exception):
    """Raised by get_current_user when no valid session exists."""


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Return the authenticated user from the session.

    Raises _AuthRedirect (handled in main.py) if no valid session is present.
    Swap this dependency's implementation for real OAuth in Step 25.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise _AuthRedirect()
    user = await db.get(User, user_id)
    if not user:
        request.session.clear()
        raise _AuthRedirect()
    return user
