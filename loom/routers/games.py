"""Games dashboard routes."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import (
    Act,
    BeatSignificanceThreshold,
    Game,
    GameMember,
    GameStatus,
    MemberRole,
    Notification,
    TieBreakingMethod,
    User,
)
from loom.rendering import templates

router = APIRouter()

MAX_GAME_PLAYERS = 5


def _find_membership(game: Game, user_id: int) -> GameMember | None:
    """Return the GameMember record for user_id in game, or None."""
    for m in game.members:
        if m.user_id == user_id:
            return m
    return None


@router.get("/games", response_class=HTMLResponse)
async def my_games(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the current user's games dashboard."""
    result = await db.execute(
        select(Game)
        .join(GameMember, GameMember.game_id == Game.id)
        .where(GameMember.user_id == current_user.id)
        .order_by(Game.name)
    )
    games = result.scalars().all()

    # Build per-game unread notification counts
    game_ids = [g.id for g in games]
    unread_counts: dict[int, int] = {g.id: 0 for g in games}
    if game_ids:
        counts_result = await db.execute(
            select(Notification.game_id, func.count(Notification.id))
            .where(
                Notification.user_id == current_user.id,
                Notification.game_id.in_(game_ids),
                Notification.read_at.is_(None),
            )
            .group_by(Notification.game_id)
        )
        for game_id, count in counts_result.all():
            unread_counts[game_id] = count

    total_unread = sum(unread_counts.values())
    return templates.TemplateResponse(
        request,
        "games.html",
        {
            "user": current_user,
            "games": games,
            "unread_counts": unread_counts,
            "total_unread": total_unread,
        },
    )


@router.post("/games", response_class=RedirectResponse)
async def create_game(
    request: Request,
    name: str = Form(...),
    pitch: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Create a new game and redirect to its dashboard."""
    game = Game(
        name=name,
        pitch=pitch or None,
        status=GameStatus.setup,
        invite_token=secrets.token_urlsafe(32),
    )
    db.add(game)
    await db.flush()
    member = GameMember(game_id=game.id, user_id=current_user.id, role=MemberRole.organizer)
    db.add(member)
    await db.commit()
    return RedirectResponse(url=f"/games/{game.id}", status_code=303)


@router.get("/games/{game_id}", response_class=HTMLResponse)
async def game_detail(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the game dashboard."""
    result = await db.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(
            selectinload(Game.members).selectinload(GameMember.user),
            selectinload(Game.acts).selectinload(Act.scenes),
        )
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    invite_url = None
    if current_member.role == MemberRole.organizer and game.invite_token:
        invite_url = str(request.base_url) + f"invite/{game.invite_token}"

    acts = sorted(game.acts, key=lambda a: a.order)
    for act in acts:
        act.scenes.sort(key=lambda s: s.order)

    return templates.TemplateResponse(
        request,
        "game_detail.html",
        {
            "game": game,
            "members": game.members,
            "current_member": current_member,
            "invite_url": invite_url,
            "max_players": MAX_GAME_PLAYERS,
            "acts": acts,
        },
    )


@router.get("/invite/{token}", response_class=HTMLResponse)
async def invite_landing(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the invite landing page for a game."""
    result = await db.execute(
        select(Game).where(Game.invite_token == token).options(selectinload(Game.members))
    )
    game = result.scalar_one_or_none()
    if game is None:
        return templates.TemplateResponse(
            request,
            "invite.html",
            {"game": None, "error": "Invite link is invalid or has been revoked."},
            status_code=404,
        )

    # If already a member, redirect to the dashboard
    user_id = request.session.get("user_id")
    if user_id and _find_membership(game, int(user_id)):
        return RedirectResponse(url=f"/games/{game.id}", status_code=303)

    return templates.TemplateResponse(
        request,
        "invite.html",
        {
            "game": game,
            "token": token,
            "member_count": len(game.members),
            "max_players": MAX_GAME_PLAYERS,
            "is_full": len(game.members) >= MAX_GAME_PLAYERS,
            "error": None,
        },
    )


@router.post("/invite/{token}", response_class=RedirectResponse, response_model=None)
async def join_game(
    token: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse | HTMLResponse:
    """Join a game via invite token."""
    result = await db.execute(
        select(Game).where(Game.invite_token == token).options(selectinload(Game.members))
    )
    game = result.scalar_one_or_none()
    if game is None:
        return templates.TemplateResponse(
            request,
            "invite.html",
            {"game": None, "error": "Invite link is invalid or has been revoked."},
            status_code=404,
        )

    # Already a member — just redirect
    if _find_membership(game, current_user.id):
        return RedirectResponse(url=f"/games/{game.id}", status_code=303)

    # Enforce player cap — re-query the count immediately before inserting to
    # narrow the TOCTOU window between the initial load and the commit.
    count_result = await db.execute(
        select(func.count(GameMember.id)).where(GameMember.game_id == game.id)
    )
    current_count = count_result.scalar()
    if current_count >= MAX_GAME_PLAYERS:
        return templates.TemplateResponse(
            request,
            "invite.html",
            {
                "game": game,
                "token": token,
                "member_count": current_count,
                "max_players": MAX_GAME_PLAYERS,
                "is_full": True,
                "error": f"This game is full (maximum {MAX_GAME_PLAYERS} players).",
            },
            status_code=409,
        )

    member = GameMember(game_id=game.id, user_id=current_user.id, role=MemberRole.player)
    db.add(member)
    await db.commit()
    return RedirectResponse(url=f"/games/{game.id}", status_code=303)


@router.get("/games/{game_id}/settings", response_class=HTMLResponse)
async def game_settings(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show game settings — readable by all members, editable by organizer only."""
    result = await db.execute(
        select(Game).where(Game.id == game_id).options(selectinload(Game.members))
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    return templates.TemplateResponse(
        request,
        "game_settings.html",
        {"game": game, "current_member": current_member},
    )


@router.post("/games/{game_id}/settings", response_class=RedirectResponse)
async def update_game_settings(
    game_id: int,
    request: Request,
    silence_timer_hours: int = Form(12),
    tie_breaking_method: str = Form("random"),
    beat_significance_threshold: str = Form("flag_obvious"),
    max_consecutive_beats: int = Form(3),
    auto_generate_narrative: str = Form(""),
    fortune_roll_contest_window_hours: str = Form(""),
    starting_tension: int = Form(5),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Update game settings (organizer only)."""
    result = await db.execute(
        select(Game).where(Game.id == game_id).options(selectinload(Game.members))
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None or current_member.role != MemberRole.organizer:
        raise HTTPException(status_code=403, detail="Only the organizer can change settings")

    game.silence_timer_hours = max(1, min(168, silence_timer_hours))
    try:
        game.tie_breaking_method = TieBreakingMethod(tie_breaking_method)
        game.beat_significance_threshold = BeatSignificanceThreshold(beat_significance_threshold)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid setting value")
    game.max_consecutive_beats = max(1, min(10, max_consecutive_beats))
    game.auto_generate_narrative = bool(auto_generate_narrative)
    game.fortune_roll_contest_window_hours = (
        max(1, min(168, int(fortune_roll_contest_window_hours)))
        if fortune_roll_contest_window_hours.strip()
        else None
    )
    game.starting_tension = max(1, min(9, starting_tension))

    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}/settings", status_code=303)


@router.post("/games/{game_id}/invite/regenerate", response_class=RedirectResponse)
async def regenerate_invite(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Regenerate the invite token for a game (organizer only)."""
    result = await db.execute(
        select(Game).where(Game.id == game_id).options(selectinload(Game.members))
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None or current_member.role != MemberRole.organizer:
        raise HTTPException(
            status_code=403, detail="Only the organizer can regenerate the invite link"
        )

    game.invite_token = secrets.token_urlsafe(32)
    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}", status_code=303)


@router.post("/games/{game_id}/pause", response_class=RedirectResponse)
async def pause_game(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Pause an active game (organizer only)."""
    result = await db.execute(
        select(Game).where(Game.id == game_id).options(selectinload(Game.members))
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None or current_member.role != MemberRole.organizer:
        raise HTTPException(status_code=403, detail="Only the organizer can pause a game")

    if game.status != GameStatus.active:
        raise HTTPException(status_code=403, detail="Only active games can be paused")

    game.status = GameStatus.paused
    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}", status_code=303)


@router.post("/games/{game_id}/resume", response_class=RedirectResponse)
async def resume_game(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Resume a paused game (organizer only)."""
    result = await db.execute(
        select(Game).where(Game.id == game_id).options(selectinload(Game.members))
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None or current_member.role != MemberRole.organizer:
        raise HTTPException(status_code=403, detail="Only the organizer can resume a game")

    if game.status != GameStatus.paused:
        raise HTTPException(status_code=403, detail="Only paused games can be resumed")

    game.status = GameStatus.active
    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}", status_code=303)


@router.post("/games/{game_id}/archive", response_class=RedirectResponse)
async def archive_game(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Archive a game (organizer only). Archived games are read-only."""
    result = await db.execute(
        select(Game).where(Game.id == game_id).options(selectinload(Game.members))
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None or current_member.role != MemberRole.organizer:
        raise HTTPException(status_code=403, detail="Only the organizer can archive a game")

    if game.status == GameStatus.archived:
        raise HTTPException(status_code=403, detail="Game is already archived")

    game.status = GameStatus.archived
    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}", status_code=303)


@router.post("/games/{game_id}/invite/revoke", response_class=RedirectResponse)
async def revoke_invite(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Revoke the invite token for a game (organizer only)."""
    result = await db.execute(
        select(Game).where(Game.id == game_id).options(selectinload(Game.members))
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None or current_member.role != MemberRole.organizer:
        raise HTTPException(status_code=403, detail="Only the organizer can revoke the invite link")

    game.invite_token = None
    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}", status_code=303)


@router.post("/games/{game_id}/prose-preference", response_class=RedirectResponse)
async def update_prose_preference(
    game_id: int,
    prose_mode_override: str = Form(default=""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Update the current player's per-game prose suggestion preference."""
    result = await db.execute(
        select(Game).where(Game.id == game_id).options(selectinload(Game.members))
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    valid_overrides = {"", "always", "never", "threshold"}
    if prose_mode_override not in valid_overrides:
        raise HTTPException(status_code=422, detail="Invalid prose mode")

    current_member.prose_mode_override = prose_mode_override or None
    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}", status_code=303)
