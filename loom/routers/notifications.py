"""Notification listing and read-status routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.config import settings
from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import Notification, User
from loom.notifications import send_digest_emails
from loom.rendering import templates

router = APIRouter()


async def _load_notification(notification_id: int, user_id: int, db: AsyncSession) -> Notification:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_view(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .options(selectinload(Notification.game))
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifications = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "notifications.html",
        {"notifications": notifications},
    )


@router.get("/notifications/unread-count")
async def unread_count(
    game_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Return JSON unread count, optionally scoped to a game."""
    query = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.read_at.is_(None),
    )
    if game_id is not None:
        query = query.where(Notification.game_id == game_id)
    result = await db.execute(query)
    count = len(result.scalars().all())
    return JSONResponse({"count": count})


@router.post("/notifications/{notification_id}/read")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    notification = await _load_notification(notification_id, current_user.id, db)
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
    await db.commit()
    return RedirectResponse(url="/notifications", status_code=302)


@router.post("/notifications/send-digests")
async def send_digests(
    db: AsyncSession = Depends(get_db),
    x_digest_key: str | None = Header(default=None, alias="X-Digest-Key"),
) -> JSONResponse:
    """Send batched digest emails for all pending notifications.

    This endpoint is intended to be called by a cron job or scheduler.
    Requires the ``X-Digest-Key`` header to match ``settings.digest_api_key``.
    Returns 503 if the digest key is not configured, 401 if the key is wrong.
    """
    if not settings.digest_api_key:
        raise HTTPException(status_code=503, detail="Digest email not configured")
    if x_digest_key != settings.digest_api_key:
        raise HTTPException(status_code=401, detail="Invalid digest key")

    notifications_sent, users_sent = await send_digest_emails(db)
    return JSONResponse({"sent": notifications_sent, "users": users_sent})


@router.post("/notifications/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
        )
    )
    now = datetime.now(timezone.utc)
    for notification in result.scalars().all():
        notification.read_at = now
    await db.commit()
    return RedirectResponse(url="/notifications", status_code=302)
