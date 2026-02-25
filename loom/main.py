from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from loom import models as _models  # noqa: F401 - registers models with Base.metadata
from loom.database import Base, engine
from loom.routers import pages


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Create all tables on startup (dev convenience; migrations handle production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Loom", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="loom/static"), name="static")
app.include_router(pages.router)
