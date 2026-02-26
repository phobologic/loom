"""Word seed table management routes."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import (
    Game,
    GameMember,
    MemberRole,
    User,
    WordSeedEntry,
    WordSeedTable,
    WordSeedWordType,
)
from loom.rendering import templates
from loom.word_seeds import ensure_game_seeds

router = APIRouter()


def _safe_referer(request: Request, fallback: str) -> str:
    """Return the Referer URL only if it is same-origin; otherwise return fallback."""
    referer = request.headers.get("referer")
    if referer and urlparse(referer).netloc == request.url.netloc:
        return referer
    return fallback


def _find_membership(game: Game, user_id: int) -> GameMember | None:
    """Return the GameMember record for user_id in game, or None."""
    for m in game.members:
        if m.user_id == user_id:
            return m
    return None


async def _load_game_with_members(game_id: int, db: AsyncSession) -> Game | None:
    result = await db.execute(
        select(Game).where(Game.id == game_id).options(selectinload(Game.members))
    )
    return result.scalar_one_or_none()


async def _load_word_seed_tables(game_id: int, db: AsyncSession) -> list[WordSeedTable]:
    """Load all word seed tables for a game, with entries eagerly loaded."""
    result = await db.execute(
        select(WordSeedTable)
        .where(WordSeedTable.game_id == game_id)
        .options(
            selectinload(WordSeedTable.entries),
        )
        .order_by(WordSeedTable.is_builtin.desc(), WordSeedTable.category)
    )
    return list(result.scalars().all())


async def _get_or_create_custom_table(game_id: int, db: AsyncSession) -> WordSeedTable:
    """Return the custom (non-builtin) WordSeedTable for a game, creating it if needed."""
    result = await db.execute(
        select(WordSeedTable).where(
            WordSeedTable.game_id == game_id,
            WordSeedTable.is_builtin == False,  # noqa: E712
        )
    )
    custom_table = result.scalar_one_or_none()
    if custom_table is None:
        custom_table = WordSeedTable(
            game_id=game_id,
            category="custom",
            is_active=True,
            is_builtin=False,
        )
        db.add(custom_table)
        await db.flush()
    return custom_table


@router.get("/games/{game_id}/word-seeds", response_class=HTMLResponse)
async def word_seeds_page(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the word seed table management page for a game."""
    game = await _load_game_with_members(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    await ensure_game_seeds(game_id, db)
    await db.commit()

    word_seed_tables = await _load_word_seed_tables(game_id, db)

    return templates.TemplateResponse(
        request,
        "word_seeds.html",
        {
            "game": game,
            "current_member": current_member,
            "current_user": current_user,
            "word_seed_tables": word_seed_tables,
        },
    )


@router.post("/games/{game_id}/word-seeds/{table_id}/toggle", response_class=RedirectResponse)
async def toggle_word_seed_table(
    game_id: int,
    table_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Toggle a builtin word seed table active or inactive (any member)."""
    game = await _load_game_with_members(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    result = await db.execute(
        select(WordSeedTable).where(WordSeedTable.id == table_id, WordSeedTable.game_id == game_id)
    )
    table = result.scalar_one_or_none()
    if table is None:
        raise HTTPException(status_code=404, detail="Word seed table not found")

    if not table.is_builtin:
        raise HTTPException(status_code=400, detail="Custom tables cannot be toggled")

    table.is_active = not table.is_active
    await db.commit()

    return RedirectResponse(
        url=_safe_referer(request, f"/games/{game_id}/word-seeds"), status_code=303
    )


@router.post("/games/{game_id}/word-seeds/entries/add", response_class=RedirectResponse)
async def add_custom_word(
    game_id: int,
    request: Request,
    word: str = Form(...),
    word_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Add a custom word to this game's word seed pool (any member)."""
    game = await _load_game_with_members(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    try:
        word_type_enum = WordSeedWordType(word_type)
    except ValueError:
        raise HTTPException(
            status_code=422, detail="Invalid word_type; must be 'action' or 'descriptor'"
        )

    word = word.strip().lower()
    if not word:
        raise HTTPException(status_code=422, detail="Word cannot be empty")

    custom_table = await _get_or_create_custom_table(game_id, db)
    db.add(WordSeedEntry(table_id=custom_table.id, word=word, word_type=word_type_enum))
    await db.commit()

    return RedirectResponse(
        url=_safe_referer(request, f"/games/{game_id}/word-seeds"), status_code=303
    )


@router.post(
    "/games/{game_id}/word-seeds/entries/{entry_id}/delete", response_class=RedirectResponse
)
async def delete_custom_word(
    game_id: int,
    entry_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Delete a custom word entry. Any member can delete their own; organizer can delete any."""
    game = await _load_game_with_members(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    result = await db.execute(
        select(WordSeedEntry)
        .join(WordSeedTable)
        .where(WordSeedEntry.id == entry_id, WordSeedTable.game_id == game_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Word entry not found")

    # Verify it's a custom (non-builtin) entry via its table
    table_result = await db.execute(select(WordSeedTable).where(WordSeedTable.id == entry.table_id))
    table = table_result.scalar_one_or_none()
    if table is None or table.is_builtin:
        raise HTTPException(status_code=400, detail="Built-in words cannot be deleted")

    is_organizer = current_member.role == MemberRole.organizer
    if not is_organizer:
        raise HTTPException(status_code=403, detail="Only the organizer can delete custom words")

    await db.delete(entry)
    await db.commit()

    return RedirectResponse(
        url=_safe_referer(request, f"/games/{game_id}/word-seeds"), status_code=303
    )
