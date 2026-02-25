"""FastAPI dependencies for Loom."""

from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from loom.database import get_db
from loom.models import User


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Return the authenticated user from the session.

    Redirects to /dev/login if no valid session is present.
    Swap this dependency's implementation for real OAuth in Step 25.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=302, headers={"Location": "/dev/login"})
    user = await db.get(User, user_id)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=302, headers={"Location": "/dev/login"})
    return user
