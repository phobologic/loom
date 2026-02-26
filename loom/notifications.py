"""Helper functions for creating in-app notifications."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from loom.models import Game, Notification, NotificationType


async def create_notification(
    db: AsyncSession,
    user_id: int,
    game_id: int | None,
    ntype: NotificationType,
    message: str,
    link: str | None = None,
) -> Notification:
    """Create and persist a single notification for one user.

    Args:
        db: Active database session.
        user_id: Recipient user ID.
        game_id: Game context, or None for system-level notifications.
        ntype: Category of notification.
        message: Human-readable description of the event.
        link: Optional URL the user can navigate to for context.

    Returns:
        The newly created Notification (not yet flushed).
    """
    notification = Notification(
        user_id=user_id,
        game_id=game_id,
        notification_type=ntype,
        message=message,
        link=link,
    )
    db.add(notification)
    return notification


async def notify_game_members(
    db: AsyncSession,
    game: Game,
    ntype: NotificationType,
    message: str,
    link: str | None = None,
    exclude_user_id: int | None = None,
) -> list[Notification]:
    """Create notifications for all members of a game.

    Args:
        db: Active database session.
        game: Game whose members should be notified (members must be loaded).
        ntype: Category of notification.
        message: Human-readable description of the event.
        link: Optional URL for context.
        exclude_user_id: Skip this user (e.g., the actor who triggered the event).

    Returns:
        List of created Notification objects (not yet flushed).
    """
    notifications: list[Notification] = []
    for member in game.members:
        if member.user_id == exclude_user_id:
            continue
        notif = await create_notification(
            db,
            user_id=member.user_id,
            game_id=game.id,
            ntype=ntype,
            message=message,
            link=link,
        )
        notifications.append(notif)
    return notifications
