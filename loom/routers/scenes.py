"""Scene creation and voting routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.database import get_db
from loom.dependencies import get_current_user
from loom.dice import DiceError
from loom.dice import roll as roll_dice
from loom.fortune_roll import compute_fortune_roll_result, is_exceptional
from loom.models import (
    Act,
    ActStatus,
    Beat,
    BeatSignificance,
    BeatStatus,
    Character,
    Event,
    EventType,
    Game,
    GameMember,
    GameStatus,
    NotificationType,
    OracleComment,
    OracleInterpretationVote,
    ProposalStatus,
    ProposalType,
    Scene,
    SceneStatus,
    User,
    Vote,
    VoteChoice,
    VoteProposal,
)
from loom.notifications import create_notification, notify_game_members
from loom.rendering import templates
from loom.voting import activate_scene, approval_threshold, is_approved, resolve_tension_vote

_IC_EVENT_TYPES = {"narrative", "roll", "oracle", "fortune_roll"}
_OOC_EVENT_TYPES = {"ooc"}

router = APIRouter()


def _find_membership(game: Game, user_id: int) -> GameMember | None:
    for m in game.members:
        if m.user_id == user_id:
            return m
    return None


async def _load_scene_for_view(scene_id: int, db: AsyncSession) -> Scene | None:
    """Load a scene with beats, events, characters, and parent act/game for access checks."""
    result = await db.execute(
        select(Scene)
        .where(Scene.id == scene_id)
        .options(
            selectinload(Scene.act).selectinload(Act.game).selectinload(Game.members),
            selectinload(Scene.act)
            .selectinload(Act.game)
            .selectinload(Game.proposals)
            .selectinload(VoteProposal.votes)
            .selectinload(Vote.voter),
            selectinload(Scene.act)
            .selectinload(Act.game)
            .selectinload(Game.proposals)
            .selectinload(VoteProposal.proposed_by),
            selectinload(Scene.characters_present),
            selectinload(Scene.beats).selectinload(Beat.author),
            selectinload(Scene.beats).selectinload(Beat.events),
            selectinload(Scene.beats)
            .selectinload(Beat.events)
            .selectinload(Event.oracle_interpretation_votes)
            .selectinload(OracleInterpretationVote.voter),
            selectinload(Scene.beats)
            .selectinload(Beat.events)
            .selectinload(Event.oracle_comments)
            .selectinload(OracleComment.author),
        )
    )
    return result.scalar_one_or_none()


def _apply_beat_filter(beats: list[Beat], filter_val: str) -> list[Beat]:
    """Return beats matching the event-type filter (all / ic / ooc)."""
    if filter_val == "ic":
        return [b for b in beats if any(e.type.value in _IC_EVENT_TYPES for e in b.events)]
    if filter_val == "ooc":
        return [b for b in beats if any(e.type.value in _OOC_EVENT_TYPES for e in b.events)]
    return beats


async def _resolve_beat_proposals(
    scene: Scene,
    current_user_id: int,
    db: AsyncSession,
) -> tuple[dict, dict, dict]:
    """Check silence timer expiry and build beat-proposal context dicts.

    Returns:
        (beat_proposals, vote_counts, my_votes) where:
        - beat_proposals: {beat_id: VoteProposal} for all beat proposals on this game
        - vote_counts: {beat_id: {"yes": int, "no": int, "suggest": int}}
        - my_votes: {beat_id: Vote | None} for the current user
    """
    game = scene.act.game
    # Use naive UTC: SQLite returns naive datetimes from DateTime(timezone=True) columns
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    beat_proposals: dict[int, VoteProposal] = {
        p.beat_id: p
        for p in game.proposals
        if p.proposal_type == ProposalType.beat_proposal and p.beat_id is not None
    }

    any_expired = False
    for beat in scene.beats:
        if beat.status == BeatStatus.proposed:
            p = beat_proposals.get(beat.id)
            if p and p.status == ProposalStatus.open and p.expires_at and now >= p.expires_at:
                p.status = ProposalStatus.approved
                beat.status = BeatStatus.canon
                if beat.author_id is not None:
                    await create_notification(
                        db,
                        user_id=beat.author_id,
                        game_id=game.id,
                        ntype=NotificationType.beat_approved,
                        message="Your beat was auto-approved (silence timer expired)",
                        link=f"/games/{game.id}/acts/{scene.act_id}/scenes/{scene.id}",
                    )
                any_expired = True
    if any_expired:
        await db.commit()

    vote_counts: dict[int, dict] = {}
    my_votes: dict[int, Vote | None] = {}
    for beat_id, p in beat_proposals.items():
        vote_counts[beat_id] = {
            "yes": sum(1 for v in p.votes if v.choice == VoteChoice.yes),
            "no": sum(1 for v in p.votes if v.choice == VoteChoice.no),
            "suggest": sum(1 for v in p.votes if v.choice == VoteChoice.suggest_modification),
        }
        my_votes[beat_id] = next((v for v in p.votes if v.voter_id == current_user_id), None)

    return beat_proposals, vote_counts, my_votes


def _build_oracle_context(
    scene: Scene, current_user_id: int
) -> tuple[dict[int, dict[int, int]], dict[int, OracleInterpretationVote | None]]:
    """Build per-event oracle vote counts and current-user vote lookup.

    Returns:
        oracle_vote_counts: {event_id: {interpretation_index: count}}
        oracle_my_votes: {event_id: OracleInterpretationVote | None}
    """
    oracle_vote_counts: dict[int, dict[int, int]] = {}
    oracle_my_votes: dict[int, OracleInterpretationVote | None] = {}

    for beat in scene.beats:
        for event in beat.events:
            if event.type != EventType.oracle:
                continue
            counts: dict[int, int] = {}
            for v in event.oracle_interpretation_votes:
                counts[v.interpretation_index] = counts.get(v.interpretation_index, 0) + 1
            oracle_vote_counts[event.id] = counts
            oracle_my_votes[event.id] = next(
                (v for v in event.oracle_interpretation_votes if v.voter_id == current_user_id),
                None,
            )

    return oracle_vote_counts, oracle_my_votes


async def _resolve_fortune_rolls(
    scene: Scene,
    current_user_id: int,
    db: AsyncSession,
) -> bool:
    """Auto-resolve any pending Fortune Rolls whose contest window has expired.

    Returns True if any fortune rolls were resolved (so caller can commit).
    """
    # Use naive UTC: SQLite returns naive datetimes from DateTime(timezone=True) columns
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    game = scene.act.game
    any_resolved = False

    for beat in scene.beats:
        for event in beat.events:
            if event.type != EventType.fortune_roll:
                continue
            if event.fortune_roll_result is not None:
                continue
            if event.fortune_roll_contested:
                continue
            if event.fortune_roll_expires_at is None:
                continue
            if now < event.fortune_roll_expires_at:
                continue

            # Contest window expired with no contest — roll now.
            result = compute_fortune_roll_result(
                event.fortune_roll_odds or "fifty_fifty",
                event.fortune_roll_tension or 5,
            )
            event.fortune_roll_result = result

            if is_exceptional(result):
                beat.significance = BeatSignificance.major
                beat.status = BeatStatus.proposed
                total_players = len(game.members)
                expires_at = now + timedelta(hours=game.silence_timer_hours)
                proposal = VoteProposal(
                    game_id=game.id,
                    proposal_type=ProposalType.beat_proposal,
                    proposed_by_id=beat.author_id,
                    beat_id=beat.id,
                    expires_at=expires_at,
                )
                db.add(proposal)
                await db.flush()
                db.add(
                    Vote(
                        proposal_id=proposal.id,
                        voter_id=beat.author_id,
                        choice=VoteChoice.yes,
                    )
                )
                if is_approved(1, total_players):
                    proposal.status = ProposalStatus.approved
                    beat.status = BeatStatus.canon
            else:
                beat.significance = BeatSignificance.minor
                beat.status = BeatStatus.canon

            any_resolved = True

    return any_resolved


async def _load_game_for_scenes(game_id: int, db: AsyncSession) -> Game | None:
    result = await db.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(
            selectinload(Game.members),
            selectinload(Game.characters).selectinload(Character.owner),
            selectinload(Game.acts).selectinload(Act.scenes).selectinload(Scene.characters_present),
            selectinload(Game.proposals).selectinload(VoteProposal.votes).selectinload(Vote.voter),
            selectinload(Game.proposals).selectinload(VoteProposal.proposed_by),
            selectinload(Game.proposals)
            .selectinload(VoteProposal.scene)
            .selectinload(Scene.characters_present),
        )
    )
    return result.scalar_one_or_none()


@router.get("/games/{game_id}/acts/{act_id}/scenes", response_class=HTMLResponse)
async def scenes_view(
    game_id: int,
    act_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show scenes for an active act, any pending scene proposal, and the proposal form."""
    game = await _load_game_for_scenes(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    act = next((a for a in game.acts if a.id == act_id), None)
    if act is None:
        raise HTTPException(status_code=404, detail="Act not found")

    if act.status not in (ActStatus.active, ActStatus.complete):
        raise HTTPException(
            status_code=403, detail="Scenes can only be viewed for an active or complete act"
        )

    scenes = sorted(act.scenes, key=lambda s: s.order)

    open_proposal = next(
        (
            p
            for p in game.proposals
            if p.status == ProposalStatus.open and p.proposal_type == ProposalType.scene_proposal
        ),
        None,
    )

    my_vote = None
    yes_count = no_count = suggest_count = 0
    if open_proposal is not None:
        my_vote = next((v for v in open_proposal.votes if v.voter_id == current_user.id), None)
        yes_count = sum(1 for v in open_proposal.votes if v.choice == VoteChoice.yes)
        no_count = sum(1 for v in open_proposal.votes if v.choice == VoteChoice.no)
        suggest_count = sum(
            1 for v in open_proposal.votes if v.choice == VoteChoice.suggest_modification
        )

    total_players = len(game.members)
    threshold = approval_threshold(total_players)

    non_proposed = [s for s in act.scenes if s.status != SceneStatus.proposed]
    default_tension = max(non_proposed, key=lambda s: s.order).tension if non_proposed else 5

    act_complete_proposal = next(
        (
            p
            for p in game.proposals
            if p.status == ProposalStatus.open
            and p.proposal_type == ProposalType.act_complete
            and p.act_id == act.id
        ),
        None,
    )
    ac_my_vote = None
    ac_yes_count = ac_no_count = ac_suggest_count = 0
    if act_complete_proposal is not None:
        ac_my_vote = next(
            (v for v in act_complete_proposal.votes if v.voter_id == current_user.id), None
        )
        ac_yes_count = sum(1 for v in act_complete_proposal.votes if v.choice == VoteChoice.yes)
        ac_no_count = sum(1 for v in act_complete_proposal.votes if v.choice == VoteChoice.no)
        ac_suggest_count = sum(
            1 for v in act_complete_proposal.votes if v.choice == VoteChoice.suggest_modification
        )

    return templates.TemplateResponse(
        request,
        "scenes.html",
        {
            "game": game,
            "act": act,
            "current_member": current_member,
            "current_user": current_user,
            "scenes": scenes,
            "characters": game.characters,
            "open_proposal": open_proposal,
            "my_vote": my_vote,
            "yes_count": yes_count,
            "no_count": no_count,
            "suggest_count": suggest_count,
            "total_players": total_players,
            "threshold": threshold,
            "default_tension": default_tension,
            "act_complete_proposal": act_complete_proposal,
            "ac_my_vote": ac_my_vote,
            "ac_yes_count": ac_yes_count,
            "ac_no_count": ac_no_count,
            "ac_suggest_count": ac_suggest_count,
        },
    )


@router.post("/games/{game_id}/acts/{act_id}/scenes", response_class=RedirectResponse)
async def propose_scene(
    game_id: int,
    act_id: int,
    request: Request,
    guiding_question: str = Form(...),
    location: str = Form(""),
    tension: int = Form(5),
    character_ids: list[int] = Form(default=[]),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Propose a new scene within the active act. Goes through the standard voting flow."""
    game = await _load_game_for_scenes(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status != GameStatus.active:
        raise HTTPException(status_code=403, detail="Game must be active to propose a scene")

    act = next((a for a in game.acts if a.id == act_id), None)
    if act is None:
        raise HTTPException(status_code=404, detail="Act not found")

    if act.status != ActStatus.active:
        raise HTTPException(status_code=403, detail="Act must be active to propose a scene")

    if not guiding_question.strip():
        raise HTTPException(status_code=422, detail="Guiding question is required")

    if not character_ids:
        raise HTTPException(status_code=422, detail="At least one character must be present")

    if not (1 <= tension <= 9):
        raise HTTPException(status_code=422, detail="Tension must be between 1 and 9")

    has_open = any(
        p.status == ProposalStatus.open and p.proposal_type == ProposalType.scene_proposal
        for p in game.proposals
    )
    if has_open:
        raise HTTPException(status_code=409, detail="A scene proposal is already pending")

    game_char_ids = {c.id for c in game.characters}
    invalid = set(character_ids) - game_char_ids
    if invalid:
        raise HTTPException(status_code=422, detail="One or more characters are not in this game")

    next_order = max((s.order for s in act.scenes), default=0) + 1

    scene = Scene(
        act_id=act.id,
        guiding_question=guiding_question.strip(),
        location=location.strip() or None,
        tension=tension,
        status=SceneStatus.proposed,
        order=next_order,
    )
    db.add(scene)
    await db.flush()
    await db.refresh(scene, ["characters_present"])

    selected_chars = [c for c in game.characters if c.id in set(character_ids)]
    scene.characters_present = selected_chars

    total_players = len(game.members)
    proposal = VoteProposal(
        game_id=game.id,
        proposal_type=ProposalType.scene_proposal,
        proposed_by_id=current_user.id,
        scene_id=scene.id,
    )
    db.add(proposal)
    await db.flush()

    db.add(Vote(proposal_id=proposal.id, voter_id=current_user.id, choice=VoteChoice.yes))

    auto_approved = is_approved(1, total_players)
    if auto_approved:
        proposal.status = ProposalStatus.approved
        activate_scene(act.scenes, scene)

    link = f"/games/{game_id}/acts/{act_id}/scenes"
    label = scene.guiding_question[:60]
    if not auto_approved:
        await notify_game_members(
            db,
            game,
            NotificationType.vote_required,
            f'Vote needed: scene proposal "{label}"',
            link=link,
            exclude_user_id=current_user.id,
        )

    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}/acts/{act_id}/scenes", status_code=303)


@router.post(
    "/games/{game_id}/acts/{act_id}/scenes/{scene_id}/complete",
    response_class=RedirectResponse,
)
async def propose_scene_complete(
    game_id: int,
    act_id: int,
    scene_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Propose completing the current scene. Goes through the standard voting flow."""
    scene = await _load_scene_for_view(scene_id, db)
    if scene is None or scene.act.id != act_id or scene.act.game.id != game_id:
        raise HTTPException(status_code=404, detail="Scene not found")

    game = scene.act.game
    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if scene.status != SceneStatus.active:
        raise HTTPException(status_code=403, detail="Scene must be active to propose completion")

    has_open = any(
        p.status == ProposalStatus.open
        and p.proposal_type == ProposalType.scene_complete
        and p.scene_id == scene.id
        for p in game.proposals
    )
    if has_open:
        raise HTTPException(
            status_code=409, detail="A scene completion proposal is already pending"
        )

    total_players = len(game.members)
    proposal = VoteProposal(
        game_id=game.id,
        proposal_type=ProposalType.scene_complete,
        proposed_by_id=current_user.id,
        scene_id=scene.id,
    )
    db.add(proposal)
    await db.flush()

    db.add(Vote(proposal_id=proposal.id, voter_id=current_user.id, choice=VoteChoice.yes))

    auto_approved = is_approved(1, total_players)
    if auto_approved:
        proposal.status = ProposalStatus.approved
        scene.status = SceneStatus.complete

    link = f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}"
    label = scene.guiding_question[:60]
    if auto_approved:
        await notify_game_members(
            db,
            game,
            NotificationType.vote_required,
            f'Scene completed: "{label}"',
            link=link,
        )
    else:
        await notify_game_members(
            db,
            game,
            NotificationType.vote_required,
            f'Vote needed: complete scene "{label}"',
            link=link,
            exclude_user_id=current_user.id,
        )

    await db.commit()
    return RedirectResponse(
        url=f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}", status_code=303
    )


@router.get("/games/{game_id}/acts/{act_id}/scenes/{scene_id}", response_class=HTMLResponse)
async def scene_detail(
    game_id: int,
    act_id: int,
    scene_id: int,
    request: Request,
    filter: str = "all",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the scene play view: beat timeline with HTMX polling and filter controls."""
    scene = await _load_scene_for_view(scene_id, db)
    if scene is None or scene.act.id != act_id or scene.act.game.id != game_id:
        raise HTTPException(status_code=404, detail="Scene not found")

    act = scene.act
    game = act.game

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if filter not in ("all", "ic", "ooc"):
        filter = "all"

    beats = sorted(scene.beats, key=lambda b: b.order)
    filtered_beats = _apply_beat_filter(beats, filter)

    beat_proposals, beat_vote_counts, beat_my_votes = await _resolve_beat_proposals(
        scene, current_user.id, db
    )
    if await _resolve_fortune_rolls(scene, current_user.id, db):
        await db.commit()
    oracle_vote_counts, oracle_my_votes = _build_oracle_context(scene, current_user.id)
    # Use naive UTC for template comparisons: SQLite returns naive datetimes
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    scene_complete_proposal = next(
        (
            p
            for p in game.proposals
            if p.status == ProposalStatus.open
            and p.proposal_type == ProposalType.scene_complete
            and p.scene_id == scene.id
        ),
        None,
    )
    sc_my_vote = None
    sc_yes_count = sc_no_count = sc_suggest_count = 0
    if scene_complete_proposal is not None:
        sc_my_vote = next(
            (v for v in scene_complete_proposal.votes if v.voter_id == current_user.id), None
        )
        sc_yes_count = sum(1 for v in scene_complete_proposal.votes if v.choice == VoteChoice.yes)
        sc_no_count = sum(1 for v in scene_complete_proposal.votes if v.choice == VoteChoice.no)
        sc_suggest_count = sum(
            1 for v in scene_complete_proposal.votes if v.choice == VoteChoice.suggest_modification
        )

    total_players = len(game.members)

    # Tension adjustment proposal for this scene (open or awaiting expiry)
    tension_adj_proposal = next(
        (
            p
            for p in game.proposals
            if p.status == ProposalStatus.open
            and p.proposal_type == ProposalType.tension_adjustment
            and p.scene_id == scene.id
        ),
        None,
    )

    # Lazy expiry: if the proposal window has closed with no full quorum, resolve now
    if (
        tension_adj_proposal is not None
        and tension_adj_proposal.expires_at is not None
        and tension_adj_proposal.expires_at.replace(tzinfo=None) < now
    ):
        yes_count = sum(1 for v in tension_adj_proposal.votes if v.choice == VoteChoice.yes)
        suggest_count = sum(
            1 for v in tension_adj_proposal.votes if v.choice == VoteChoice.suggest_modification
        )
        no_count = sum(1 for v in tension_adj_proposal.votes if v.choice == VoteChoice.no)
        delta = resolve_tension_vote(
            yes_count, suggest_count, no_count, tension_adj_proposal.tension_delta or 0
        )
        scene.tension = max(1, min(9, scene.tension + delta))
        tension_adj_proposal.status = ProposalStatus.approved
        await db.commit()
        tension_adj_proposal = None  # resolved — hide from template

    ta_my_vote = None
    ta_yes_count = ta_suggest_count = ta_no_count = 0
    if tension_adj_proposal is not None:
        ta_my_vote = next(
            (v for v in tension_adj_proposal.votes if v.voter_id == current_user.id), None
        )
        ta_yes_count = sum(1 for v in tension_adj_proposal.votes if v.choice == VoteChoice.yes)
        ta_suggest_count = sum(
            1 for v in tension_adj_proposal.votes if v.choice == VoteChoice.suggest_modification
        )
        ta_no_count = sum(1 for v in tension_adj_proposal.votes if v.choice == VoteChoice.no)

    ta_proposed_tension = (
        max(1, min(9, scene.tension + (tension_adj_proposal.tension_delta or 0)))
        if tension_adj_proposal is not None
        else None
    )

    return templates.TemplateResponse(
        request,
        "scene_detail.html",
        {
            "game": game,
            "act": act,
            "scene": scene,
            "beats": filtered_beats,
            "filter": filter,
            "beat_proposals": beat_proposals,
            "beat_vote_counts": beat_vote_counts,
            "beat_my_votes": beat_my_votes,
            "oracle_vote_counts": oracle_vote_counts,
            "oracle_my_votes": oracle_my_votes,
            "current_user_id": current_user.id,
            "total_players": total_players,
            "now": now,
            "scene_complete_proposal": scene_complete_proposal,
            "sc_my_vote": sc_my_vote,
            "sc_yes_count": sc_yes_count,
            "sc_no_count": sc_no_count,
            "sc_suggest_count": sc_suggest_count,
            "threshold": approval_threshold(total_players),
            "tension_adj_proposal": tension_adj_proposal,
            "ta_my_vote": ta_my_vote,
            "ta_yes_count": ta_yes_count,
            "ta_suggest_count": ta_suggest_count,
            "ta_no_count": ta_no_count,
            "ta_proposed_tension": ta_proposed_tension,
        },
    )


_BEAT_EVENT_TYPES = {"narrative", "ooc", "roll"}


@router.post(
    "/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats",
    response_class=RedirectResponse,
)
async def submit_beat(
    game_id: int,
    act_id: int,
    scene_id: int,
    event_type: list[str] = Form(default=[]),
    event_content: list[str] = Form(default=[]),
    event_notation: list[str] = Form(default=[]),
    event_reason: list[str] = Form(default=[]),
    beat_significance: str = Form(default="minor"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Submit a beat with one or more events (narrative, OOC, or roll)."""
    scene = await _load_scene_for_view(scene_id, db)
    if scene is None or scene.act.id != act_id or scene.act.game.id != game_id:
        raise HTTPException(status_code=404, detail="Scene not found")

    game = scene.act.game
    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if scene.status != SceneStatus.active:
        raise HTTPException(
            status_code=403, detail="Beats can only be submitted for an active scene"
        )

    # Pad shorter lists to align with event_type
    n = len(event_type)
    padded_content = (list(event_content) + [""] * n)[:n]
    padded_notation = (list(event_notation) + [""] * n)[:n]
    padded_reason = (list(event_reason) + [""] * n)[:n]

    # Validate and build event specs
    event_specs: list[dict] = []
    for etype, econtent, enotation, ereason in zip(
        event_type, padded_content, padded_notation, padded_reason
    ):
        etype = etype.strip()
        if etype not in _BEAT_EVENT_TYPES:
            raise HTTPException(status_code=422, detail=f"Invalid event type: {etype!r}")

        if etype in ("narrative", "ooc"):
            content = econtent.strip()
            if not content:
                raise HTTPException(
                    status_code=422,
                    detail=f"{etype.capitalize()} event requires content",
                )
            event_specs.append({"type": etype, "content": content})
        else:  # roll
            notation = enotation.strip()
            if not notation:
                raise HTTPException(status_code=422, detail="Roll event requires notation")
            try:
                result = roll_dice(notation)
            except DiceError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            event_specs.append(
                {
                    "type": "roll",
                    "notation": notation,
                    "result": result,
                    "reason": ereason.strip() or None,
                }
            )

    if not event_specs:
        raise HTTPException(status_code=422, detail="A beat must have at least one event")

    beat_significance = beat_significance.strip().lower()
    if beat_significance not in (BeatSignificance.minor.value, BeatSignificance.major.value):
        raise HTTPException(status_code=422, detail="Invalid beat significance")
    significance = BeatSignificance(beat_significance)
    status = BeatStatus.canon if significance == BeatSignificance.minor else BeatStatus.proposed

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

    for i, spec in enumerate(event_specs):
        if spec["type"] in ("narrative", "ooc"):
            event = Event(
                beat_id=beat.id,
                type=EventType[spec["type"]],
                content=spec["content"],
                order=i + 1,
            )
        else:  # roll
            event = Event(
                beat_id=beat.id,
                type=EventType.roll,
                roll_notation=spec["notation"],
                roll_result=spec["result"],
                content=spec["reason"],
                order=i + 1,
            )
        db.add(event)

    scene_link = f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}"

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
        db.add(
            Vote(
                proposal_id=proposal.id,
                voter_id=current_user.id,
                choice=VoteChoice.yes,
            )
        )
        beat_auto_approved = is_approved(1, total_players)
        if beat_auto_approved:
            proposal.status = ProposalStatus.approved
            beat.status = BeatStatus.canon
        else:
            await notify_game_members(
                db,
                game,
                NotificationType.vote_required,
                "Vote needed: major beat submitted",
                link=scene_link,
                exclude_user_id=current_user.id,
            )

    await notify_game_members(
        db,
        game,
        NotificationType.new_beat,
        "A new beat was submitted",
        link=scene_link,
        exclude_user_id=current_user.id,
    )

    await db.commit()

    return RedirectResponse(
        url=scene_link,
        status_code=303,
    )


@router.get("/games/{game_id}/acts/{act_id}/scenes/{scene_id}/beats", response_class=HTMLResponse)
async def beats_partial(
    game_id: int,
    act_id: int,
    scene_id: int,
    request: Request,
    filter: str = "all",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """HTMX partial: return the beat timeline fragment for polling updates."""
    scene = await _load_scene_for_view(scene_id, db)
    if scene is None or scene.act.id != act_id or scene.act.game.id != game_id:
        raise HTTPException(status_code=404, detail="Scene not found")

    game = scene.act.game
    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if filter not in ("all", "ic", "ooc"):
        filter = "all"

    beats = sorted(scene.beats, key=lambda b: b.order)
    filtered_beats = _apply_beat_filter(beats, filter)

    beat_proposals, beat_vote_counts, beat_my_votes = await _resolve_beat_proposals(
        scene, current_user.id, db
    )
    if await _resolve_fortune_rolls(scene, current_user.id, db):
        await db.commit()
    oracle_vote_counts, oracle_my_votes = _build_oracle_context(scene, current_user.id)
    # Use naive UTC for template comparisons: SQLite returns naive datetimes
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    return templates.TemplateResponse(
        request,
        "_beats_partial.html",
        {
            "beats": filtered_beats,
            "beat_proposals": beat_proposals,
            "beat_vote_counts": beat_vote_counts,
            "beat_my_votes": beat_my_votes,
            "oracle_vote_counts": oracle_vote_counts,
            "oracle_my_votes": oracle_my_votes,
            "current_user_id": current_user.id,
            "game": scene.act.game,
            "act": scene.act,
            "scene": scene,
            "now": now,
        },
    )
