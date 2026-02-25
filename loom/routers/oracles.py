"""Oracle invocation routes: word pair generation and interpretation creation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.ai import stubs as ai_stubs
from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import (
    Act,
    Beat,
    BeatSignificance,
    BeatStatus,
    Event,
    EventType,
    Game,
    GameMember,
    ProposalStatus,
    ProposalType,
    Scene,
    SceneStatus,
    User,
    Vote,
    VoteChoice,
    VoteProposal,
)
from loom.rendering import templates
from loom.voting import is_approved
from loom.word_seeds import ensure_game_seeds, random_word_pair

router = APIRouter()


def _find_membership(game: Game, user_id: int) -> GameMember | None:
    for m in game.members:
        if m.user_id == user_id:
            return m
    return None


async def _load_scene(scene_id: int, db: AsyncSession) -> Scene | None:
    result = await db.execute(
        select(Scene)
        .where(Scene.id == scene_id)
        .options(
            selectinload(Scene.act).selectinload(Act.game).selectinload(Game.members),
            selectinload(Scene.beats),
        )
    )
    return result.scalar_one_or_none()


@router.get(
    "/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
    response_class=HTMLResponse,
)
async def oracle_form(
    game_id: int,
    act_id: int,
    scene_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the oracle invocation form with a freshly generated word pair."""
    scene = await _load_scene(scene_id, db)
    if scene is None or scene.act.id != act_id or scene.act.game.id != game_id:
        raise HTTPException(status_code=404, detail="Scene not found")

    game = scene.act.game
    act = scene.act

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if scene.status != SceneStatus.active:
        raise HTTPException(status_code=403, detail="Oracle can only be invoked in an active scene")

    await ensure_game_seeds(game_id, db)
    await db.commit()

    action, descriptor = await random_word_pair(game_id, db)

    return templates.TemplateResponse(
        request,
        "oracle.html",
        {
            "game": game,
            "act": act,
            "scene": scene,
            "action": action,
            "descriptor": descriptor,
        },
    )


@router.post(
    "/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
    response_class=RedirectResponse,
)
async def invoke_oracle(
    game_id: int,
    act_id: int,
    scene_id: int,
    question: str = Form(...),
    word_action: str = Form(...),
    word_descriptor: str = Form(...),
    beat_significance: str = Form(default="minor"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Submit an oracle invocation: creates a beat with an oracle event."""
    scene = await _load_scene(scene_id, db)
    if scene is None or scene.act.id != act_id or scene.act.game.id != game_id:
        raise HTTPException(status_code=404, detail="Scene not found")

    game = scene.act.game

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if scene.status != SceneStatus.active:
        raise HTTPException(status_code=403, detail="Oracle can only be invoked in an active scene")

    if not question.strip():
        raise HTTPException(status_code=422, detail="Oracle question is required")

    beat_significance = beat_significance.strip().lower()
    if beat_significance not in (BeatSignificance.minor.value, BeatSignificance.major.value):
        raise HTTPException(status_code=422, detail="Invalid beat significance")

    significance = BeatSignificance(beat_significance)
    status = BeatStatus.canon if significance == BeatSignificance.minor else BeatStatus.proposed

    interpretations = ai_stubs.oracle_interpretations(
        question.strip(), (word_action.strip(), word_descriptor.strip())
    )

    next_order = max((b.order for b in scene.beats), default=0) + 1
    beat = Beat(
        scene_id=scene.id,
        author_id=current_user.id,
        significance=significance,
        status=status,
        order=next_order,
    )
    db.add(beat)
    await db.flush()

    event = Event(
        beat_id=beat.id,
        type=EventType.oracle,
        oracle_query=question.strip(),
        word_seed_action=word_action.strip() or None,
        word_seed_descriptor=word_descriptor.strip() or None,
        order=1,
    )
    event.interpretations = interpretations
    db.add(event)

    if significance == BeatSignificance.major:
        total_players = len(game.members)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=game.silence_timer_hours)
        proposal = VoteProposal(
            game_id=game.id,
            proposal_type=ProposalType.beat_proposal,
            proposed_by_id=current_user.id,
            beat_id=beat.id,
            expires_at=expires_at,
        )
        db.add(proposal)
        await db.flush()
        db.add(Vote(proposal_id=proposal.id, voter_id=current_user.id, choice=VoteChoice.yes))
        if is_approved(1, total_players):
            proposal.status = ProposalStatus.approved
            beat.status = BeatStatus.canon

    await db.commit()

    return RedirectResponse(
        url=f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}",
        status_code=303,
    )
