"""Email provider abstraction for Loom notification delivery.

When ``settings.email_enabled`` is ``False`` (the default), all send calls
are no-ops logged at DEBUG level — no SMTP server is required to run Loom.
"""

from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

import aiosmtplib

from loom.config import settings

logger = logging.getLogger(__name__)


class EmailProvider(Protocol):
    """Interface for email delivery."""

    async def send(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: str,
    ) -> None:
        """Send a single email.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body_text: Plain-text body (always included).
            body_html: HTML body (included as alternative part).
        """
        ...


class NoOpEmailProvider:
    """No-op provider used when email_enabled=False."""

    async def send(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: str,
    ) -> None:
        """Log and discard — email delivery is disabled."""
        logger.debug("Email disabled, skipping send to %s: %s", to, subject)


class SmtpEmailProvider:
    """aiosmtplib-backed SMTP provider.

    Args:
        host: SMTP server hostname.
        port: SMTP server port.
        username: SMTP auth username (empty = no auth).
        password: SMTP auth password.
        from_address: Envelope sender address.
        use_tls: Whether to use STARTTLS.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        from_address: str,
        use_tls: bool,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_address = from_address
        self._use_tls = use_tls

    async def send(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: str,
    ) -> None:
        """Send an email via SMTP.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body_text: Plain-text body.
            body_html: HTML body.

        Raises:
            aiosmtplib.SMTPException: On delivery failure.
        """
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self._from_address
        message["To"] = to
        message.attach(MIMEText(body_text, "plain"))
        message.attach(MIMEText(body_html, "html"))

        kwargs: dict = {
            "hostname": self._host,
            "port": self._port,
            "start_tls": self._use_tls,
        }
        if self._username:
            kwargs["username"] = self._username
            kwargs["password"] = self._password

        await aiosmtplib.send(message, **kwargs)
        logger.debug("Email sent to %s: %s", to, subject)


def get_email_provider() -> NoOpEmailProvider | SmtpEmailProvider:
    """Return the configured email provider.

    Returns a :class:`NoOpEmailProvider` when ``email_enabled`` is ``False``,
    otherwise a :class:`SmtpEmailProvider` using settings from config.
    """
    if not settings.email_enabled:
        return NoOpEmailProvider()
    return SmtpEmailProvider(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        from_address=settings.smtp_from_address,
        use_tls=settings.smtp_use_tls,
    )
