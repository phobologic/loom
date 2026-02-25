from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware

from loom import models as _models  # noqa: F401 - registers models with Base.metadata
from loom.config import settings
from loom.database import AsyncSessionLocal, Base, engine
from loom.models import User
from loom.routers import auth, games, pages

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
    await _seed_dev_users()
    yield


app = FastAPI(title="Loom", lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)

app.mount("/static", StaticFiles(directory="loom/static"), name="static")
app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(games.router)
