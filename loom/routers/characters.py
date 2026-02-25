"""Character creation and management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import Character, Game, GameMember, GameStatus, MemberRole, User
from loom.rendering import templates

router = APIRouter()


def _find_membership(game: Game, user_id: int) -> GameMember | None:
    """Return the GameMember record for user_id in game, or None."""
    for m in game.members:
        if m.user_id == user_id:
            return m
    return None


def _find_character(game: Game, char_id: int) -> Character | None:
    """Return the Character with char_id in game, or None."""
    for c in game.characters:
        if c.id == char_id:
            return c
    return None


def _my_character(game: Game, user_id: int) -> Character | None:
    """Return the current user's character in game, or None."""
    for c in game.characters:
        if c.owner_id == user_id:
            return c
    return None


async def _load_game_with_characters(game_id: int, db: AsyncSession) -> Game | None:
    result = await db.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(
            selectinload(Game.members),
            selectinload(Game.characters).selectinload(Character.owner),
        )
    )
    return result.scalar_one_or_none()


@router.get("/games/{game_id}/characters", response_class=HTMLResponse)
async def characters_page(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show character list and creation form."""
    game = await _load_game_with_characters(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status == GameStatus.setup:
        raise HTTPException(
            status_code=403,
            detail="Character creation is not available until Session 0 is complete",
        )

    my_char = _my_character(game, current_user.id)

    return templates.TemplateResponse(
        request,
        "characters.html",
        {
            "game": game,
            "current_member": current_member,
            "current_user": current_user,
            "characters": game.characters,
            "my_character": my_char,
            "editing": None,
        },
    )


@router.post("/games/{game_id}/characters", response_class=RedirectResponse)
async def create_character(
    game_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    notes: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Create a character for the current user."""
    game = await _load_game_with_characters(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status not in (GameStatus.active, GameStatus.paused):
        raise HTTPException(status_code=403, detail="Character creation requires an active game")

    if _my_character(game, current_user.id) is not None:
        raise HTTPException(status_code=400, detail="You already have a character in this game")

    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Character name cannot be empty")
    if len(name) > 100:
        raise HTTPException(status_code=422, detail="Character name cannot exceed 100 characters")

    db.add(
        Character(
            game_id=game_id,
            owner_id=current_user.id,
            name=name,
            description=description.strip() or None,
            notes=notes.strip() or None,
        )
    )
    await db.commit()

    return RedirectResponse(url=f"/games/{game_id}/characters", status_code=303)


@router.get("/games/{game_id}/characters/{char_id}/edit", response_class=HTMLResponse)
async def edit_character_page(
    game_id: int,
    char_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the edit form for a character."""
    game = await _load_game_with_characters(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    character = _find_character(game, char_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    is_owner = character.owner_id == current_user.id
    is_organizer = current_member.role == MemberRole.organizer
    if not is_owner and not is_organizer:
        raise HTTPException(status_code=403, detail="You can only edit your own character")

    my_char = _my_character(game, current_user.id)

    return templates.TemplateResponse(
        request,
        "characters.html",
        {
            "game": game,
            "current_member": current_member,
            "current_user": current_user,
            "characters": game.characters,
            "my_character": my_char,
            "editing": character,
        },
    )


@router.post("/games/{game_id}/characters/{char_id}/edit", response_class=RedirectResponse)
async def update_character(
    game_id: int,
    char_id: int,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    notes: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Update a character's fields."""
    game = await _load_game_with_characters(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status == GameStatus.archived:
        raise HTTPException(status_code=403, detail="Cannot edit characters in an archived game")

    character = _find_character(game, char_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")

    is_owner = character.owner_id == current_user.id
    is_organizer = current_member.role == MemberRole.organizer
    if not is_owner and not is_organizer:
        raise HTTPException(status_code=403, detail="You can only edit your own character")

    name = name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Character name cannot be empty")
    if len(name) > 100:
        raise HTTPException(status_code=422, detail="Character name cannot exceed 100 characters")

    character.name = name
    character.description = description.strip() or None
    character.notes = notes.strip() or None
    await db.commit()

    return RedirectResponse(url=f"/games/{game_id}/characters", status_code=303)
