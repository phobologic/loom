"""Helper functions for creating in-app notifications and dispatching email."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from textwrap import shorten

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession

from loom.config import settings
from loom.email import EmailProvider, get_email_provider
from loom.models import EmailPref, Game, GameMember, Notification, NotificationType, User

logger = logging.getLogger(__name__)


def resolve_email_pref(user: User, game_id: int | None = None) -> EmailPref:
    """Return the effective email preference for a user, respecting per-game overrides.

    Uses SQLAlchemy inspection to avoid touching unloaded attributes (which would
    raise ``MissingGreenlet`` in an async context and taint the session).  When
    ``memberships`` is not loaded, the per-game override check is skipped and the
    global preference is returned.  When ``email_pref`` is not loaded, ``digest``
    is returned as a safe default.

    Args:
        user: The user whose preference is being resolved.
        game_id: Game context to check for a per-game override.  Pass ``None`` for
            the global preference only.

    Returns:
        The resolved :class:`EmailPref` value.
    """
    try:
        state = sa_inspect(user)
        unloaded = state.unloaded
    except Exception:
        # Non-ORM object (e.g. mock in tests) — treat all attributes as loaded.
        unloaded = frozenset()

    if game_id is not None and "memberships" not in unloaded:
        for membership in user.memberships:
            if membership.game_id == game_id and membership.email_pref_override:
                try:
                    return EmailPref(membership.email_pref_override)
                except ValueError:
                    logger.warning(
                        "Invalid email_pref_override %r for user %d game %d",
                        membership.email_pref_override,
                        user.id,
                        game_id,
                    )

    if "email_pref" in unloaded:
        logger.debug("email_pref not loaded for user %d, defaulting to digest", user.id)
        return EmailPref.digest

    return user.email_pref


def _build_email_body(notification: Notification) -> tuple[str, str]:
    """Build plain-text and HTML email bodies for a notification.

    Args:
        notification: The notification to format.

    Returns:
        Tuple of (plain_text, html).
    """
    link = notification.link or ""
    if link and not link.startswith("http"):
        link = f"{settings.app_base_url}{link}"

    plain = notification.message
    if link:
        plain = f"{plain}\n\n{link}"

    if link:
        html = f'<p>{notification.message}</p><p><a href="{link}">View in Loom →</a></p>'
    else:
        html = f"<p>{notification.message}</p>"

    return plain, html


async def _send_notification_email(
    provider: EmailProvider,
    notification: Notification,
    user: User,
) -> None:
    """Send a single notification email to a user.

    Args:
        provider: Email provider to use for delivery.
        notification: The notification to email.
        user: The recipient; must have a non-null ``email`` field.
    """
    if not user.email:
        logger.debug("User %d has no email address, skipping email", user.id)
        return

    subject = shorten(notification.message, width=80, placeholder="…")
    body_text, body_html = _build_email_body(notification)
    await provider.send(
        to=user.email,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
    )


async def create_notification(
    db: AsyncSession,
    user_id: int,
    game_id: int | None,
    ntype: NotificationType,
    message: str,
    link: str | None = None,
    user: User | None = None,
) -> Notification:
    """Create and persist a single notification for one user.

    If the resolved email preference for the user is ``immediate`` and
    ``settings.email_enabled`` is ``True``, an email is sent synchronously
    before this function returns.

    Args:
        db: Active database session.
        user_id: Recipient user ID.
        game_id: Game context, or None for system-level notifications.
        ntype: Category of notification.
        message: Human-readable description of the event.
        link: Optional URL the user can navigate to for context.
        user: Optional pre-loaded User object (with memberships).  When provided,
            used to resolve the email preference without an extra DB query.

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

    # Attempt immediate email dispatch if the user is pre-loaded.
    # resolve_email_pref uses SQLAlchemy inspection internally to avoid
    # touching unloaded attributes — MissingGreenlet is never raised.
    if user is not None:
        pref = resolve_email_pref(user, game_id)
        if pref == EmailPref.immediate:
            provider = get_email_provider()
            try:
                await _send_notification_email(provider, notification, user)
                notification.emailed_at = datetime.now(tz=timezone.utc)
            except Exception:
                logger.exception("Failed to send immediate email to user %d", user_id)

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
        game: Game whose members should be notified (members must be loaded,
            including ``member.user`` with ``user.memberships`` for email dispatch).
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
        # Pass the loaded user only if the relationship is already in memory.
        # Accessing an unloaded relationship in async context raises
        # MissingGreenlet, which taints the session's transaction even if caught.
        loaded_user: User | None = None
        try:
            member_state = sa_inspect(member)
            if "user" not in member_state.unloaded:
                loaded_user = member.user  # type: ignore[assignment]
        except Exception:
            pass

        notif = await create_notification(
            db,
            user_id=member.user_id,
            game_id=game.id,
            ntype=ntype,
            message=message,
            link=link,
            user=loaded_user,
        )
        notifications.append(notif)
    return notifications


async def collect_digest_notifications(
    db: AsyncSession,
) -> dict[int, list[Notification]]:
    """Query all pending digest notifications grouped by user_id.

    A notification is pending for digest when:
    - ``emailed_at`` is NULL
    - The recipient's resolved email preference is ``digest``

    Args:
        db: Active database session.

    Returns:
        Mapping of user_id → list of unsent Notification rows.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Notification)
        .where(Notification.emailed_at.is_(None))
        .options(
            selectinload(Notification.user).selectinload(User.memberships),
        )
    )
    all_pending = result.scalars().all()

    grouped: dict[int, list[Notification]] = {}
    for notif in all_pending:
        user = notif.user
        pref = resolve_email_pref(user, notif.game_id)
        if pref != EmailPref.digest:
            continue
        grouped.setdefault(notif.user_id, []).append(notif)

    return grouped


async def send_digest_emails(
    db: AsyncSession,
) -> tuple[int, int]:
    """Batch and send digest emails for all pending notifications.

    Collects all unsent notifications for digest-preference users, sends one
    summary email per user, and marks each notification's ``emailed_at``.

    Args:
        db: Active database session.

    Returns:
        Tuple of (notifications_emailed, users_emailed).
    """
    grouped = await collect_digest_notifications(db)
    provider = get_email_provider()
    notifications_sent = 0
    users_sent = 0

    for user_id, notifs in grouped.items():
        user = notifs[0].user
        if not user.email:
            logger.debug("User %d has no email, skipping digest", user_id)
            continue

        subject = f"Loom: {len(notifs)} update{'s' if len(notifs) != 1 else ''} waiting for you"
        lines_text = []
        lines_html = []
        for n in notifs:
            link = n.link or ""
            if link and not link.startswith("http"):
                link = f"{settings.app_base_url}{link}"
            lines_text.append(f"• {n.message}" + (f"\n  {link}" if link else ""))
            lines_html.append(
                f"<li>{n.message}" + (f' — <a href="{link}">View →</a>' if link else "") + "</li>"
            )

        body_text = "Your Loom updates:\n\n" + "\n\n".join(lines_text)
        body_html = "<p>Your Loom updates:</p><ul>" + "".join(lines_html) + "</ul>"

        now = datetime.now(tz=timezone.utc)
        try:
            await provider.send(
                to=user.email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
            )
            for n in notifs:
                n.emailed_at = now
            notifications_sent += len(notifs)
            users_sent += 1
        except Exception:
            logger.exception("Failed to send digest email to user %d", user_id)

    if notifications_sent:
        await db.commit()

    return notifications_sent, users_sent
