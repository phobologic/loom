"""Authentication routes — OAuth (Google, Discord) and dev-only fallback.

Real OAuth is the primary auth mechanism. The /dev/login routes are only
available when settings.environment != "production".
"""

from __future__ import annotations

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from loom.config import settings
from loom.database import get_db
from loom.models import User
from loom.rendering import templates

router = APIRouter()

# ---------------------------------------------------------------------------
# OAuth client setup
# ---------------------------------------------------------------------------

oauth = OAuth()

oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

oauth.register(
    name="discord",
    client_id=settings.discord_client_id,
    client_secret=settings.discord_client_secret,
    access_token_url="https://discord.com/api/oauth2/token",
    authorize_url="https://discord.com/api/oauth2/authorize",
    api_base_url="https://discord.com/api/",
    client_kwargs={"scope": "identify email"},
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _is_dev() -> bool:
    return settings.environment != "production"


async def _upsert_user(
    *,
    provider: str,
    subject: str,
    email: str | None,
    display_name: str,
    db: AsyncSession,
) -> User:
    """Find or create a user for the given OAuth identity.

    Lookup order:
    1. Match on (oauth_provider, oauth_subject) — returning user.
    2. Match on email — link existing account to this OAuth identity.
    3. Create a new user.
    """
    # Primary lookup: OAuth identity
    result = await db.execute(
        select(User).where(
            User.oauth_provider == provider,
            User.oauth_subject == subject,
        )
    )
    user = result.scalar_one_or_none()

    if user is not None:
        # Refresh email/name if they changed upstream
        if email and user.email != email:
            user.email = email
        await db.commit()
        return user

    # Secondary lookup: account linking by email
    if email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is not None:
            user.oauth_provider = provider
            user.oauth_subject = subject
            await db.commit()
            return user

    # Create new account
    user = User(
        display_name=display_name,
        email=email,
        oauth_provider=provider,
        oauth_subject=subject,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Login page
# ---------------------------------------------------------------------------


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """Show the OAuth login page."""
    return templates.TemplateResponse(
        request,
        "login.html",
        {"is_dev": _is_dev()},
    )


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


@router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    """Clear the session and redirect to /login."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------


@router.get("/auth/google")
async def auth_google(request: Request) -> RedirectResponse:
    """Redirect the user to Google's OAuth consent screen."""
    redirect_uri = str(request.url_for("auth_google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)  # type: ignore[attr-defined]


@router.get("/auth/google/callback", name="auth_google_callback")
async def auth_google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle Google OAuth callback and sign the user in."""
    token = await oauth.google.authorize_access_token(request)  # type: ignore[attr-defined]
    userinfo = token.get("userinfo") or await oauth.google.userinfo(token=token)  # type: ignore[attr-defined]

    subject = str(userinfo["sub"])
    email = userinfo.get("email")
    display_name = userinfo.get("name") or userinfo.get("email") or subject

    user = await _upsert_user(
        provider="google",
        subject=subject,
        email=email,
        display_name=display_name,
        db=db,
    )
    request.session["user_id"] = user.id
    return RedirectResponse(url="/games", status_code=303)


# ---------------------------------------------------------------------------
# Discord OAuth
# ---------------------------------------------------------------------------


@router.get("/auth/discord")
async def auth_discord(request: Request) -> RedirectResponse:
    """Redirect the user to Discord's OAuth consent screen."""
    redirect_uri = str(request.url_for("auth_discord_callback"))
    return await oauth.discord.authorize_redirect(request, redirect_uri)  # type: ignore[attr-defined]


@router.get("/auth/discord/callback", name="auth_discord_callback")
async def auth_discord_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle Discord OAuth callback and sign the user in."""
    token = await oauth.discord.authorize_access_token(request)  # type: ignore[attr-defined]
    resp = await oauth.discord.get("users/@me", token=token)  # type: ignore[attr-defined]
    userinfo = resp.json()

    subject = str(userinfo["id"])
    email = userinfo.get("email")
    username = userinfo.get("global_name") or userinfo.get("username") or subject

    user = await _upsert_user(
        provider="discord",
        subject=subject,
        email=email,
        display_name=username,
        db=db,
    )
    request.session["user_id"] = user.id
    return RedirectResponse(url="/games", status_code=303)


# ---------------------------------------------------------------------------
# Dev-only login (gated behind non-production environment)
# ---------------------------------------------------------------------------


@router.get("/dev/login", response_class=HTMLResponse)
async def dev_login_page(request: Request, db: AsyncSession = Depends(get_db)) -> HTMLResponse:
    """Show the dev login page with all seeded users."""
    if not _is_dev():
        raise HTTPException(status_code=404)
    result = await db.execute(select(User).order_by(User.display_name))
    users = result.scalars().all()
    return templates.TemplateResponse(request, "dev_login.html", {"users": users})


@router.post("/dev/login")
async def dev_login(
    request: Request,
    user_id: int = Form(...),
) -> RedirectResponse:
    """Set the session to the chosen user and redirect to /games."""
    if not _is_dev():
        raise HTTPException(status_code=404)
    request.session["user_id"] = user_id
    return RedirectResponse(url="/games", status_code=303)


@router.post("/dev/logout")
async def dev_logout(request: Request) -> RedirectResponse:
    """Clear the session and redirect to /dev/login."""
    if not _is_dev():
        raise HTTPException(status_code=404)
    request.session.clear()
    return RedirectResponse(url="/dev/login", status_code=303)
