from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from loom import models as _models  # noqa: F401 - registers models with Base.metadata
from loom.config import settings
from loom.database import AsyncSessionLocal, Base, engine
from loom.dependencies import _AuthRedirect
from loom.models import User
from loom.routers import (
    acts,
    auth,
    characters,
    games,
    notifications,
    oracles,
    pages,
    profile,
    safety_tools,
    scenes,
    session0,
    word_seeds,
    world_document,
)

_DEV_USERS = ["Alice", "Bob", "Charlie"]


async def _seed_dev_users() -> None:
    """Insert named dev users if they don't already exist."""
    async with AsyncSessionLocal() as session:
        for name in _DEV_USERS:
            result = await session.execute(select(User).where(User.display_name == name))
            if result.scalar_one_or_none() is None:
                session.add(User(display_name=name))
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if settings.environment != "production":
        await _seed_dev_users()
    yield


app = FastAPI(title="Loom", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)
app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(games.router)
app.include_router(acts.router)
app.include_router(session0.router)
app.include_router(safety_tools.router)
app.include_router(word_seeds.router)
app.include_router(world_document.router)
app.include_router(characters.router)
app.include_router(scenes.router)
app.include_router(oracles.router)
app.include_router(notifications.router)


@app.exception_handler(_AuthRedirect)
async def auth_redirect_handler(request: Request, exc: _AuthRedirect) -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=302)
