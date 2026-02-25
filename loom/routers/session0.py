"""Session 0 wizard routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.ai.stubs import session0_synthesis
from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import (
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    PromptStatus,
    Session0Prompt,
    Session0Response,
    User,
)
from loom.rendering import templates

router = APIRouter()

_DEFAULT_PROMPTS = [
    "What genre and aesthetic define this world?",
    "What is the overall tone — dark and gritty, hopeful, mysterious, comedic?",
    "Describe the setting: time period, location, and world details.",
    "What is the central tension or mystery that drives the story?",
    "What themes are most important to explore in this game?",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_membership(game: Game, user_id: int) -> GameMember | None:
    """Return the GameMember record for user_id in game, or None."""
    for m in game.members:
        if m.user_id == user_id:
            return m
    return None


def _advance_wizard(prompts: list[Session0Prompt], after_order: int) -> Session0Prompt | None:
    """Mark the next pending prompt (with order > after_order) as active.

    The caller has already changed the current prompt's status before calling this,
    so we can't rely on finding the 'active' prompt — we use the order position instead.
    """
    for p in sorted(prompts, key=lambda p: p.order):
        if p.order > after_order and p.status == PromptStatus.pending:
            p.status = PromptStatus.active
            return p
    return None


def _all_done(prompts: list[Session0Prompt]) -> bool:
    """Return True when every prompt is complete or skipped."""
    return all(p.status in (PromptStatus.complete, PromptStatus.skipped) for p in prompts)


async def _load_game_with_session0(game_id: int, db: AsyncSession) -> Game:
    """Load game with members and session0_prompts eagerly."""
    result = await db.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(
            selectinload(Game.members),
            selectinload(Game.session0_prompts)
            .selectinload(Session0Prompt.responses)
            .selectinload(Session0Response.user),
        )
    )
    return result.scalar_one_or_none()


async def _seed_defaults(game: Game, db: AsyncSession) -> None:
    """Create the five default prompts for a game if none exist."""
    for i, question in enumerate(_DEFAULT_PROMPTS):
        status = PromptStatus.active if i == 0 else PromptStatus.pending
        db.add(
            Session0Prompt(
                game_id=game.id,
                order=i,
                question=question,
                is_default=True,
                status=status,
            )
        )
    await db.flush()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/games/{game_id}/session0", response_class=RedirectResponse)
async def session0_index(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Redirect to the current active prompt, seeding defaults on first visit."""
    # Load game (members only — we just need the membership check here)
    result = await db.execute(
        select(Game).where(Game.id == game_id).options(selectinload(Game.members))
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    # Load prompts directly (avoids identity-map caching issues after seeding)
    prompts_result = await db.execute(
        select(Session0Prompt)
        .where(Session0Prompt.game_id == game_id)
        .order_by(Session0Prompt.order)
    )
    prompts = list(prompts_result.scalars().all())

    if not prompts:
        await _seed_defaults(game, db)
        await db.commit()
        prompts_result = await db.execute(
            select(Session0Prompt)
            .where(Session0Prompt.game_id == game_id)
            .order_by(Session0Prompt.order)
        )
        prompts = list(prompts_result.scalars().all())

    # Find the active prompt
    active = next((p for p in prompts if p.status == PromptStatus.active), None)
    if active is None:
        # Advance to first pending (handles return visit after all were completed)
        first_pending = next((p for p in prompts if p.status == PromptStatus.pending), None)
        if first_pending:
            first_pending.status = PromptStatus.active
            await db.commit()
            active = first_pending
        else:
            # All prompts done — redirect to last one
            active = prompts[-1]

    return RedirectResponse(url=f"/games/{game_id}/session0/{active.id}", status_code=303)


@router.get("/games/{game_id}/session0/{prompt_id}", response_class=HTMLResponse)
async def session0_prompt(
    game_id: int,
    prompt_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show a Session 0 prompt with contributions and synthesis."""
    game = await _load_game_with_session0(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    prompt = next((p for p in game.session0_prompts if p.id == prompt_id), None)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    my_response = next((r for r in prompt.responses if r.user_id == current_user.id), None)

    return templates.TemplateResponse(
        request,
        "session0_wizard.html",
        {
            "game": game,
            "prompt": prompt,
            "all_prompts": list(game.session0_prompts),
            "responses": prompt.responses,
            "my_response": my_response,
            "current_member": current_member,
            "all_done": _all_done(list(game.session0_prompts)),
        },
    )


@router.post("/games/{game_id}/session0/{prompt_id}/respond", response_class=RedirectResponse)
async def respond_to_prompt(
    game_id: int,
    prompt_id: int,
    request: Request,
    content: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Submit or update the current user's contribution to a prompt."""
    game = await _load_game_with_session0(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    prompt = next((p for p in game.session0_prompts if p.id == prompt_id), None)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if prompt.status != PromptStatus.active:
        raise HTTPException(status_code=403, detail="This prompt is not currently active")

    existing = next((r for r in prompt.responses if r.user_id == current_user.id), None)
    if existing:
        existing.content = content.strip()
    else:
        db.add(
            Session0Response(
                prompt_id=prompt_id,
                user_id=current_user.id,
                content=content.strip(),
            )
        )
    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}/session0/{prompt_id}", status_code=303)


@router.post("/games/{game_id}/session0/{prompt_id}/synthesize", response_class=RedirectResponse)
async def synthesize_prompt(
    game_id: int,
    prompt_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Generate an AI synthesis of player contributions (organizer only)."""
    game = await _load_game_with_session0(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None or current_member.role != MemberRole.organizer:
        raise HTTPException(status_code=403, detail="Only the organizer can synthesize")

    prompt = next((p for p in game.session0_prompts if p.id == prompt_id), None)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    inputs = []
    if game.pitch:
        inputs.append(game.pitch)
    inputs.extend(r.content for r in prompt.responses)

    prompt.synthesis = session0_synthesis(inputs)
    prompt.synthesis_accepted = False
    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}/session0/{prompt_id}", status_code=303)


@router.post("/games/{game_id}/session0/{prompt_id}/regenerate", response_class=RedirectResponse)
async def regenerate_synthesis(
    game_id: int,
    prompt_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Re-run synthesis, overwriting the previous result (organizer only)."""
    game = await _load_game_with_session0(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None or current_member.role != MemberRole.organizer:
        raise HTTPException(status_code=403, detail="Only the organizer can regenerate")

    prompt = next((p for p in game.session0_prompts if p.id == prompt_id), None)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    inputs = []
    if game.pitch:
        inputs.append(game.pitch)
    inputs.extend(r.content for r in prompt.responses)

    prompt.synthesis = session0_synthesis(inputs)
    prompt.synthesis_accepted = False
    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}/session0/{prompt_id}", status_code=303)


@router.post("/games/{game_id}/session0/{prompt_id}/accept", response_class=RedirectResponse)
async def accept_synthesis(
    game_id: int,
    prompt_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Accept the current synthesis and advance the wizard (organizer only)."""
    game = await _load_game_with_session0(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None or current_member.role != MemberRole.organizer:
        raise HTTPException(status_code=403, detail="Only the organizer can accept")

    prompt = next((p for p in game.session0_prompts if p.id == prompt_id), None)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt.synthesis_accepted = True
    prompt.status = PromptStatus.complete

    next_prompt = _advance_wizard(list(game.session0_prompts), after_order=prompt.order)
    await db.commit()

    if next_prompt:
        return RedirectResponse(url=f"/games/{game_id}/session0/{next_prompt.id}", status_code=303)
    return RedirectResponse(url=f"/games/{game_id}/session0/{prompt_id}", status_code=303)


@router.post("/games/{game_id}/session0/{prompt_id}/skip", response_class=RedirectResponse)
async def skip_prompt(
    game_id: int,
    prompt_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Skip the current prompt and advance the wizard (organizer only)."""
    game = await _load_game_with_session0(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None or current_member.role != MemberRole.organizer:
        raise HTTPException(status_code=403, detail="Only the organizer can skip prompts")

    prompt = next((p for p in game.session0_prompts if p.id == prompt_id), None)
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt.status = PromptStatus.skipped

    next_prompt = _advance_wizard(list(game.session0_prompts), after_order=prompt.order)
    await db.commit()

    if next_prompt:
        return RedirectResponse(url=f"/games/{game_id}/session0/{next_prompt.id}", status_code=303)
    return RedirectResponse(url=f"/games/{game_id}/session0/{prompt_id}", status_code=303)


@router.post("/games/{game_id}/session0/prompts/add", response_class=RedirectResponse)
async def add_custom_prompt(
    game_id: int,
    request: Request,
    question: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Append a custom prompt to the wizard (organizer only)."""
    game = await _load_game_with_session0(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None or current_member.role != MemberRole.organizer:
        raise HTTPException(status_code=403, detail="Only the organizer can add prompts")

    prompts = list(game.session0_prompts)
    next_order = max((p.order for p in prompts), default=-1) + 1
    new_prompt = Session0Prompt(
        game_id=game_id,
        order=next_order,
        question=question.strip(),
        is_default=False,
        status=PromptStatus.pending,
    )
    db.add(new_prompt)
    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}/session0", status_code=303)


@router.post("/games/{game_id}/session0/prompts/{prompt_id}/move", response_class=RedirectResponse)
async def move_prompt(
    game_id: int,
    prompt_id: int,
    request: Request,
    direction: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Move a pending prompt up or down in the sequence (organizer only)."""
    game = await _load_game_with_session0(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None or current_member.role != MemberRole.organizer:
        raise HTTPException(status_code=403, detail="Only the organizer can reorder prompts")

    target = next((p for p in game.session0_prompts if p.id == prompt_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if target.status not in (PromptStatus.pending,):
        raise HTTPException(status_code=403, detail="Only pending prompts can be reordered")

    sorted_prompts = sorted(game.session0_prompts, key=lambda p: p.order)
    idx = next(i for i, p in enumerate(sorted_prompts) if p.id == prompt_id)

    if direction == "up" and idx > 0:
        neighbor = sorted_prompts[idx - 1]
        target.order, neighbor.order = neighbor.order, target.order
    elif direction == "down" and idx < len(sorted_prompts) - 1:
        neighbor = sorted_prompts[idx + 1]
        target.order, neighbor.order = neighbor.order, target.order
    # Boundary cases: no-op

    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}/session0", status_code=303)


@router.post("/games/{game_id}/session0/complete", response_class=RedirectResponse)
async def complete_session0(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Complete Session 0 and transition the game to active (organizer only)."""
    game = await _load_game_with_session0(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None or current_member.role != MemberRole.organizer:
        raise HTTPException(status_code=403, detail="Only the organizer can complete Session 0")

    prompts = list(game.session0_prompts)
    if not _all_done(prompts):
        raise HTTPException(status_code=403, detail="All prompts must be complete or skipped first")

    game.status = GameStatus.active
    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}", status_code=303)
