"""Tests for Step 39: Email Notifications (loo-ld95)."""

from __future__ import annotations

import unittest.mock
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from loom.models import (
    EmailPref,
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    Notification,
    NotificationType,
    User,
)
from loom.notifications import resolve_email_pref

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _login(client: AsyncClient, user_id: int) -> None:
    await client.post("/dev/login", data={"user_id": str(user_id)}, follow_redirects=False)


async def _create_active_game_with_bob(client: AsyncClient, db: AsyncSession) -> int:
    """Alice (id=1) creates and owns the game; Bob (id=2) is a player."""
    await _login(client, 1)
    r = await client.post(
        "/games", data={"name": "Email Test Game", "pitch": "A pitch"}, follow_redirects=False
    )
    game_id = int(r.headers["location"].rsplit("/", 1)[-1])

    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one()
    game.status = GameStatus.active

    result = await db.execute(select(User).where(User.id == 2))
    bob = result.scalar_one()
    db.add(GameMember(game_id=game_id, user_id=bob.id, role=MemberRole.player))
    await db.flush()
    db.expire_all()
    return game_id


# ---------------------------------------------------------------------------
# resolve_email_pref unit tests
# ---------------------------------------------------------------------------


class TestResolveEmailPref:
    """resolve_email_pref returns global or per-game override correctly."""

    def _make_user(self, pref: str) -> MagicMock:
        user = MagicMock(spec=User)
        user.email_pref = EmailPref(pref)
        user.memberships = []
        return user

    def _make_membership(self, game_id: int, override: str | None) -> MagicMock:
        m = MagicMock(spec=GameMember)
        m.game_id = game_id
        m.email_pref_override = override
        return m

    def test_returns_global_pref_when_no_game_id(self):
        user = self._make_user("digest")
        assert resolve_email_pref(user) == EmailPref.digest

    def test_returns_global_pref_when_no_override_for_game(self):
        user = self._make_user("immediate")
        user.memberships = [self._make_membership(game_id=5, override=None)]
        assert resolve_email_pref(user, game_id=5) == EmailPref.immediate

    def test_returns_override_when_set(self):
        user = self._make_user("immediate")
        user.memberships = [self._make_membership(game_id=5, override="off")]
        assert resolve_email_pref(user, game_id=5) == EmailPref.off

    def test_override_off_beats_global_immediate(self):
        user = self._make_user("immediate")
        user.memberships = [self._make_membership(game_id=7, override="off")]
        assert resolve_email_pref(user, game_id=7) == EmailPref.off

    def test_falls_back_to_global_for_different_game(self):
        user = self._make_user("digest")
        user.memberships = [self._make_membership(game_id=5, override="off")]
        # Game 99 has no override — should return global
        assert resolve_email_pref(user, game_id=99) == EmailPref.digest

    def test_invalid_override_value_falls_back_to_global(self):
        user = self._make_user("digest")
        user.memberships = [self._make_membership(game_id=5, override="bogus")]
        assert resolve_email_pref(user, game_id=5) == EmailPref.digest


# ---------------------------------------------------------------------------
# Profile — email_pref persisted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_profile_email_pref_persisted(client: AsyncClient, db: AsyncSession):
    """POST /profile saves the email_pref field."""
    await _login(client, 1)

    r = await client.post(
        "/profile",
        data={
            "display_name": "Alice",
            "email_pref": "immediate",
            "prose_mode": "always",
            "prose_threshold_words": "50",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    db.expire_all()
    result = await db.execute(select(User).where(User.id == 1))
    alice = result.scalar_one()
    assert alice.email_pref == EmailPref.immediate


@pytest.mark.asyncio
async def test_profile_invalid_email_pref_ignored(client: AsyncClient, db: AsyncSession):
    """An unrecognised email_pref value is silently ignored (original value kept)."""
    await _login(client, 1)

    # Set a known starting value
    result = await db.execute(select(User).where(User.id == 1))
    alice = result.scalar_one()
    alice.email_pref = EmailPref.digest
    await db.flush()

    await client.post(
        "/profile",
        data={
            "display_name": "Alice",
            "email_pref": "bogus",
            "prose_mode": "always",
            "prose_threshold_words": "50",
        },
        follow_redirects=False,
    )

    db.expire_all()
    result = await db.execute(select(User).where(User.id == 1))
    alice = result.scalar_one()
    assert alice.email_pref == EmailPref.digest


# ---------------------------------------------------------------------------
# Per-game email preference override
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_game_email_pref_override_set(client: AsyncClient, db: AsyncSession):
    """POST /games/{id}/email-preference sets the per-game override."""
    game_id = await _create_active_game_with_bob(client, db)
    await _login(client, 1)

    r = await client.post(
        f"/games/{game_id}/email-preference",
        data={"email_pref_override": "off"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    db.expire_all()
    result = await db.execute(
        select(GameMember).where(GameMember.game_id == game_id, GameMember.user_id == 1)
    )
    member = result.scalar_one()
    assert member.email_pref_override == "off"


@pytest.mark.asyncio
async def test_game_email_pref_override_cleared(client: AsyncClient, db: AsyncSession):
    """Posting empty string clears the per-game override (falls back to account default)."""
    game_id = await _create_active_game_with_bob(client, db)
    await _login(client, 1)

    # Set override first
    result = await db.execute(
        select(GameMember).where(GameMember.game_id == game_id, GameMember.user_id == 1)
    )
    member = result.scalar_one()
    member.email_pref_override = "off"
    await db.flush()

    r = await client.post(
        f"/games/{game_id}/email-preference",
        data={"email_pref_override": ""},
        follow_redirects=False,
    )
    assert r.status_code == 303

    db.expire_all()
    result = await db.execute(
        select(GameMember).where(GameMember.game_id == game_id, GameMember.user_id == 1)
    )
    member = result.scalar_one()
    assert member.email_pref_override is None


@pytest.mark.asyncio
async def test_game_email_pref_invalid_value(client: AsyncClient, db: AsyncSession):
    """An invalid preference value returns 422."""
    game_id = await _create_active_game_with_bob(client, db)
    await _login(client, 1)

    r = await client.post(
        f"/games/{game_id}/email-preference",
        data={"email_pref_override": "weekly"},
        follow_redirects=False,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_game_email_pref_non_member_rejected(client: AsyncClient, db: AsyncSession):
    """A user who is not a game member cannot set a preference."""
    game_id = await _create_active_game_with_bob(client, db)
    await _login(client, 3)  # Charlie is not a member

    r = await client.post(
        f"/games/{game_id}/email-preference",
        data={"email_pref_override": "off"},
        follow_redirects=False,
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Digest endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_digests_missing_key(client: AsyncClient, db: AsyncSession):
    """Missing X-Digest-Key header returns 401."""
    from loom.config import settings

    with unittest.mock.patch.object(settings, "digest_api_key", "secret123"):
        r = await client.post("/notifications/send-digests")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_send_digests_wrong_key(client: AsyncClient, db: AsyncSession):
    """Wrong X-Digest-Key value returns 401."""
    from loom.config import settings

    with unittest.mock.patch.object(settings, "digest_api_key", "secret123"):
        r = await client.post(
            "/notifications/send-digests",
            headers={"X-Digest-Key": "wrongkey"},
        )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_send_digests_not_configured(client: AsyncClient, db: AsyncSession):
    """Empty digest_api_key returns 503."""
    from loom.config import settings

    with unittest.mock.patch.object(settings, "digest_api_key", ""):
        r = await client.post(
            "/notifications/send-digests",
            headers={"X-Digest-Key": ""},
        )
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_send_digests_batches_pending(client: AsyncClient, db: AsyncSession):
    """Pending digest notifications are emailed and marked as emailed_at."""
    from loom.config import settings
    from loom.notifications import send_digest_emails

    # Give Alice an email address and set digest pref
    result = await db.execute(select(User).where(User.id == 1))
    alice = result.scalar_one()
    alice.email = "alice@example.com"
    alice.email_pref = EmailPref.digest

    # Create two unsent notifications for Alice
    game_id = await _create_active_game_with_bob(client, db)
    n1 = Notification(
        user_id=1,
        game_id=game_id,
        notification_type=NotificationType.new_beat,
        message="A new beat was added.",
        link=f"/games/{game_id}",
    )
    n2 = Notification(
        user_id=1,
        game_id=game_id,
        notification_type=NotificationType.oracle_ready,
        message="An oracle result is ready.",
        link=f"/games/{game_id}",
    )
    db.add_all([n1, n2])
    await db.flush()
    n1_id = n1.id  # capture before expire_all clears __dict__

    sent_calls: list = []

    async def _mock_send(to, subject, body_text, body_html):
        sent_calls.append({"to": to, "subject": subject})

    mock_provider = MagicMock()
    mock_provider.send = _mock_send

    with (
        unittest.mock.patch("loom.notifications.get_email_provider", return_value=mock_provider),
        unittest.mock.patch.object(settings, "digest_api_key", "secret123"),
    ):
        r = await client.post(
            "/notifications/send-digests",
            headers={"X-Digest-Key": "secret123"},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["users"] >= 1
    assert data["sent"] >= 2

    # Verify notifications have emailed_at set
    db.expire_all()
    result = await db.execute(select(Notification).where(Notification.id == n1_id))
    n1_refreshed = result.scalar_one()
    assert n1_refreshed.emailed_at is not None


# ---------------------------------------------------------------------------
# Immediate send path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_immediate_send_on_create_notification(db: AsyncSession):
    """create_notification sends email immediately for immediate-pref users."""
    from loom.notifications import create_notification

    user = MagicMock(spec=User)
    user.id = 99
    user.email = "test@example.com"
    user.email_pref = EmailPref.immediate
    user.memberships = []

    sent: list = []

    async def _mock_send(to, subject, body_text, body_html):
        sent.append(to)

    mock_provider = MagicMock()
    mock_provider.send = _mock_send

    with unittest.mock.patch("loom.notifications.get_email_provider", return_value=mock_provider):
        notif = await create_notification(
            db,
            user_id=99,
            game_id=None,
            ntype=NotificationType.new_beat,
            message="A beat was added.",
            link="/games/1",
            user=user,
        )

    assert len(sent) == 1
    assert sent[0] == "test@example.com"
    assert notif.emailed_at is not None


@pytest.mark.asyncio
async def test_no_immediate_send_when_disabled(db: AsyncSession):
    """create_notification does not send email for off-pref users."""
    from loom.notifications import create_notification

    user = MagicMock(spec=User)
    user.id = 99
    user.email = "test@example.com"
    user.email_pref = EmailPref.off
    user.memberships = []

    sent: list = []

    async def _mock_send(to, subject, body_text, body_html):
        sent.append(to)  # pragma: no cover

    mock_provider = MagicMock()
    mock_provider.send = _mock_send

    with unittest.mock.patch("loom.notifications.get_email_provider", return_value=mock_provider):
        notif = await create_notification(
            db,
            user_id=99,
            game_id=None,
            ntype=NotificationType.new_beat,
            message="A beat was added.",
            user=user,
        )

    assert len(sent) == 0
    assert notif.emailed_at is None


@pytest.mark.asyncio
async def test_no_immediate_send_for_digest_pref(db: AsyncSession):
    """create_notification does not send email for digest-pref users (saved for batch)."""
    from loom.notifications import create_notification

    user = MagicMock(spec=User)
    user.id = 99
    user.email = "test@example.com"
    user.email_pref = EmailPref.digest
    user.memberships = []

    sent: list = []

    async def _mock_send(to, subject, body_text, body_html):
        sent.append(to)  # pragma: no cover

    mock_provider = MagicMock()
    mock_provider.send = _mock_send

    with unittest.mock.patch("loom.notifications.get_email_provider", return_value=mock_provider):
        notif = await create_notification(
            db,
            user_id=99,
            game_id=None,
            ntype=NotificationType.new_beat,
            message="A beat was added.",
            user=user,
        )

    assert len(sent) == 0
    assert notif.emailed_at is None
