"""Oracle invocation routes: word pair generation and interpretation creation."""

from __future__ import annotations

import random as _random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.ai import stubs as ai_stubs
from loom.database import get_db
from loom.dependencies import get_current_user
from loom.fortune_roll import (
    FORTUNE_ROLL_ODDS,
    ODDS_LABELS,
    PROBABILITY_TABLE,
    RESULT_LABELS,
    fortune_roll_contest_window_hours,
)
from loom.models import (
    Act,
    Beat,
    BeatSignificance,
    BeatStatus,
    Event,
    EventType,
    Game,
    GameMember,
    NotificationType,
    OracleComment,
    OracleInterpretationVote,
    OracleType,
    ProposalStatus,
    ProposalType,
    Scene,
    SceneStatus,
    TieBreakingMethod,
    User,
    Vote,
    VoteChoice,
    VoteProposal,
)
from loom.notifications import notify_game_members
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
    oracle_type: str = Form(default="world"),
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

    oracle_type = oracle_type.strip().lower()
    if oracle_type not in (OracleType.personal.value, OracleType.world.value):
        oracle_type = OracleType.world.value

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
        oracle_type=oracle_type,
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

    scene_link = f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}"
    if oracle_type == OracleType.world.value:
        await notify_game_members(
            db,
            game,
            NotificationType.oracle_ready,
            f'Oracle interpretations ready: "{question.strip()[:60]}"',
            link=scene_link,
            exclude_user_id=current_user.id,
        )

    await db.commit()

    return RedirectResponse(
        url=scene_link,
        status_code=303,
    )


async def _load_oracle_event(event_id: int, game_id: int, db: AsyncSession) -> Event | None:
    """Load an oracle Event with its beat, game membership, votes, and comments."""
    result = await db.execute(
        select(Event)
        .where(Event.id == event_id)
        .options(
            selectinload(Event.beat)
            .selectinload(Beat.scene)
            .selectinload(Scene.act)
            .selectinload(Act.game)
            .selectinload(Game.members),
            selectinload(Event.oracle_interpretation_votes).selectinload(
                OracleInterpretationVote.voter
            ),
            selectinload(Event.oracle_comments).selectinload(OracleComment.author),
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        return None
    if event.beat.scene.act.game.id != game_id:
        return None
    return event


def _scene_redirect(event: Event) -> str:
    """Return the scene URL for an oracle event."""
    beat = event.beat
    scene = beat.scene
    act = scene.act
    game = act.game
    return f"/games/{game.id}/acts/{act.id}/scenes/{scene.id}"


@router.post("/games/{game_id}/oracle/events/{event_id}/vote", response_class=RedirectResponse)
async def vote_on_interpretation(
    game_id: int,
    event_id: int,
    interpretation_index: int = Form(...),
    alternative_text: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Cast a vote for an oracle interpretation (or propose a custom alternative)."""
    event = await _load_oracle_event(event_id, game_id, db)
    if event is None or event.type != EventType.oracle:
        raise HTTPException(status_code=404, detail="Oracle event not found")

    game = event.beat.scene.act.game
    if _find_membership(game, current_user.id) is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if event.oracle_selected_interpretation is not None:
        raise HTTPException(status_code=403, detail="Oracle has already been resolved")

    alt = alternative_text.strip()
    if interpretation_index == -1 and not alt:
        raise HTTPException(status_code=422, detail="Alternative text is required for custom vote")
    if interpretation_index != -1:
        if interpretation_index < 0 or interpretation_index >= len(event.interpretations):
            raise HTTPException(status_code=422, detail="Invalid interpretation index")

    vote = OracleInterpretationVote(
        event_id=event_id,
        voter_id=current_user.id,
        interpretation_index=interpretation_index,
        alternative_text=alt if interpretation_index == -1 else None,
    )
    db.add(vote)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="You have already voted on this oracle")

    await db.commit()
    return RedirectResponse(url=_scene_redirect(event), status_code=303)


@router.post("/games/{game_id}/oracle/events/{event_id}/comment", response_class=RedirectResponse)
async def comment_on_oracle(
    game_id: int,
    event_id: int,
    text: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Add a comment to an oracle invocation."""
    event = await _load_oracle_event(event_id, game_id, db)
    if event is None or event.type != EventType.oracle:
        raise HTTPException(status_code=404, detail="Oracle event not found")

    game = event.beat.scene.act.game
    if _find_membership(game, current_user.id) is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if event.oracle_selected_interpretation is not None:
        raise HTTPException(status_code=403, detail="Oracle has already been resolved")

    if not text.strip():
        raise HTTPException(status_code=422, detail="Comment text is required")

    db.add(OracleComment(event_id=event_id, author_id=current_user.id, text=text.strip()))
    await db.commit()
    return RedirectResponse(url=_scene_redirect(event), status_code=303)


@router.post("/games/{game_id}/oracle/events/{event_id}/select", response_class=RedirectResponse)
async def select_interpretation(
    game_id: int,
    event_id: int,
    interpretation_index: int = Form(...),
    alternative_text: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Invoker selects the final oracle interpretation.

    Pass interpretation_index=-2 to auto-resolve using the game's tie-breaking method.
    Pass interpretation_index=-1 with alternative_text for a custom selection.
    Pass interpretation_index=0..N to select a generated interpretation by index.
    """
    event = await _load_oracle_event(event_id, game_id, db)
    if event is None or event.type != EventType.oracle:
        raise HTTPException(status_code=404, detail="Oracle event not found")

    if event.beat.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the oracle invoker can select")

    if event.oracle_selected_interpretation is not None:
        raise HTTPException(status_code=403, detail="Oracle has already been resolved")

    game = event.beat.scene.act.game

    # interpretation_index == -2 → apply tie-breaking from vote tallies
    if interpretation_index == -2:
        votes = event.oracle_interpretation_votes
        if not votes:
            raise HTTPException(status_code=422, detail="No votes to resolve tie from")

        counts: dict[int, int] = {}
        for v in votes:
            counts[v.interpretation_index] = counts.get(v.interpretation_index, 0) + 1

        max_count = max(counts.values())
        tied = [idx for idx, cnt in counts.items() if cnt == max_count]

        if game.tie_breaking_method == TieBreakingMethod.proposer and len(tied) == 1:
            winner_idx = tied[0]
        else:
            # random and challenger both use random selection among tied options
            winner_idx = _random.choice(tied)

        if winner_idx == -1:
            # find the most-voted alternative text
            alt_votes = [v for v in votes if v.interpretation_index == -1]
            selected_text = alt_votes[0].alternative_text or ""
        else:
            selected_text = event.interpretations[winner_idx]

    elif interpretation_index == -1:
        alt = alternative_text.strip()
        if not alt:
            raise HTTPException(status_code=422, detail="Alternative text is required")
        selected_text = alt

    else:
        if interpretation_index < 0 or interpretation_index >= len(event.interpretations):
            raise HTTPException(status_code=422, detail="Invalid interpretation index")
        selected_text = event.interpretations[interpretation_index]

    event.oracle_selected_interpretation = selected_text
    await db.commit()
    return RedirectResponse(url=_scene_redirect(event), status_code=303)


# ---------------------------------------------------------------------------
# Fortune Roll routes
# ---------------------------------------------------------------------------


async def _load_fortune_roll_event(event_id: int, game_id: int, db: AsyncSession) -> Event | None:
    """Load a fortune_roll Event with its beat/scene/game chain."""
    result = await db.execute(
        select(Event)
        .where(Event.id == event_id)
        .options(
            selectinload(Event.beat)
            .selectinload(Beat.scene)
            .selectinload(Scene.act)
            .selectinload(Act.game)
            .selectinload(Game.members),
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        return None
    if event.beat.scene.act.game.id != game_id:
        return None
    return event


@router.get(
    "/games/{game_id}/acts/{act_id}/scenes/{scene_id}/fortune-roll",
    response_class=HTMLResponse,
)
async def fortune_roll_form(
    game_id: int,
    act_id: int,
    scene_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the Fortune Roll form."""
    scene = await _load_scene(scene_id, db)
    if scene is None or scene.act.id != act_id or scene.act.game.id != game_id:
        raise HTTPException(status_code=404, detail="Scene not found")

    game = scene.act.game
    act = scene.act

    if _find_membership(game, current_user.id) is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if scene.status != SceneStatus.active:
        raise HTTPException(
            status_code=403, detail="Fortune Roll can only be invoked in an active scene"
        )

    return templates.TemplateResponse(
        request,
        "fortune_roll.html",
        {
            "game": game,
            "act": act,
            "scene": scene,
            "odds_options": FORTUNE_ROLL_ODDS,
            "odds_labels": ODDS_LABELS,
            "probability_table": PROBABILITY_TABLE,
            "result_labels": RESULT_LABELS,
        },
    )


@router.post(
    "/games/{game_id}/acts/{act_id}/scenes/{scene_id}/fortune-roll",
    response_class=RedirectResponse,
)
async def invoke_fortune_roll(
    game_id: int,
    act_id: int,
    scene_id: int,
    question: str = Form(...),
    odds: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Submit a Fortune Roll: creates a pending beat+event, starts the contest window."""
    scene = await _load_scene(scene_id, db)
    if scene is None or scene.act.id != act_id or scene.act.game.id != game_id:
        raise HTTPException(status_code=404, detail="Scene not found")

    game = scene.act.game

    if _find_membership(game, current_user.id) is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if scene.status != SceneStatus.active:
        raise HTTPException(
            status_code=403, detail="Fortune Roll can only be invoked in an active scene"
        )

    if not question.strip():
        raise HTTPException(status_code=422, detail="Fortune Roll question is required")

    if odds not in FORTUNE_ROLL_ODDS:
        raise HTTPException(status_code=422, detail="Invalid odds setting")

    window_hours = fortune_roll_contest_window_hours(
        game.silence_timer_hours, game.fortune_roll_contest_window_hours
    )
    expires_at = datetime.now(timezone.utc) + timedelta(hours=window_hours)

    next_order = max((b.order for b in scene.beats), default=0) + 1
    beat = Beat(
        scene_id=scene.id,
        author_id=current_user.id,
        significance=BeatSignificance.minor,
        status=BeatStatus.proposed,
        order=next_order,
    )
    db.add(beat)
    await db.flush()

    event = Event(
        beat_id=beat.id,
        type=EventType.fortune_roll,
        oracle_query=question.strip(),
        fortune_roll_odds=odds,
        fortune_roll_tension=scene.tension,
        fortune_roll_result=None,
        fortune_roll_expires_at=expires_at,
        fortune_roll_contested=False,
        order=1,
    )
    db.add(event)
    await db.commit()

    return RedirectResponse(
        url=f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}",
        status_code=303,
    )


@router.post(
    "/games/{game_id}/fortune-roll/events/{event_id}/contest",
    response_class=RedirectResponse,
)
async def contest_fortune_roll(
    game_id: int,
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Contest the odds on a pending Fortune Roll."""
    event = await _load_fortune_roll_event(event_id, game_id, db)
    if event is None or event.type != EventType.fortune_roll:
        raise HTTPException(status_code=404, detail="Fortune Roll event not found")

    game = event.beat.scene.act.game
    if _find_membership(game, current_user.id) is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if event.fortune_roll_result is not None:
        raise HTTPException(status_code=403, detail="Fortune Roll has already resolved")

    event.fortune_roll_contested = True
    await notify_game_members(
        db,
        game,
        NotificationType.fortune_roll_contested,
        "A Fortune Roll is being contested",
        link=_scene_redirect(event),
        exclude_user_id=current_user.id,
    )
    await db.commit()
    return RedirectResponse(url=_scene_redirect(event), status_code=303)


@router.post(
    "/games/{game_id}/fortune-roll/events/{event_id}/reaffirm",
    response_class=RedirectResponse,
)
async def reaffirm_fortune_roll(
    game_id: int,
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Invoker reaffirms the odds after a contest, restarting the window."""
    event = await _load_fortune_roll_event(event_id, game_id, db)
    if event is None or event.type != EventType.fortune_roll:
        raise HTTPException(status_code=404, detail="Fortune Roll event not found")

    if event.beat.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the Fortune Roll invoker can reaffirm")

    if event.fortune_roll_result is not None:
        raise HTTPException(status_code=403, detail="Fortune Roll has already resolved")

    game = event.beat.scene.act.game
    window_hours = fortune_roll_contest_window_hours(
        game.silence_timer_hours, game.fortune_roll_contest_window_hours
    )
    event.fortune_roll_contested = False
    event.fortune_roll_expires_at = datetime.now(timezone.utc) + timedelta(hours=window_hours)
    await db.commit()
    return RedirectResponse(url=_scene_redirect(event), status_code=303)
