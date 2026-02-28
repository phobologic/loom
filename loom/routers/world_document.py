"""World document and voting routes."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.ai.client import (
    evaluate_tension_adjustment,
)
from loom.ai.client import (
    generate_scene_narrative as _ai_generate_scene_narrative,
)
from loom.ai.client import (
    generate_world_document as _ai_generate_world_document,
)
from loom.ai.client import (
    suggest_character_updates as _ai_suggest_character_updates,
)
from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import (
    Act,
    ActStatus,
    Beat,
    BeatStatus,
    Character,
    CharacterUpdateCategory,
    CharacterUpdateStatus,
    CharacterUpdateSuggestion,
    Game,
    GameMember,
    GameStatus,
    NotificationType,
    ProposalStatus,
    ProposalType,
    Scene,
    SceneStatus,
    Session0Prompt,
    User,
    Vote,
    VoteChoice,
    VoteProposal,
    WorldDocument,
)
from loom.notifications import create_notification
from loom.rendering import templates
from loom.routers.acts import _compile_act_narrative
from loom.routers.relationships import _scan_beat_for_relationships
from loom.routers.world_entries import _scan_beat_for_world_entries
from loom.voting import (
    activate_act,
    activate_scene,
    approval_threshold,
    is_approved,
    resolve_tension_vote,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_membership(game: Game, user_id: int) -> GameMember | None:
    for m in game.members:
        if m.user_id == user_id:
            return m
    return None


def _collect_session0_data(game: Game) -> dict:
    """Build a dict from session0 prompts for world doc generation."""
    prompts = []
    for p in game.session0_prompts:
        if p.is_safety_tools:
            continue
        prompts.append(
            {
                "question": p.question,
                "synthesis": p.synthesis,
                "responses": [r.content for r in p.responses],
            }
        )
    return {
        "game_name": game.name,
        "pitch": game.pitch,
        "prompts": prompts,
    }


async def _load_game_for_voting(game_id: int, db: AsyncSession) -> Game | None:
    """Load game with all relationships needed for world doc / voting."""
    result = await db.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(
            selectinload(Game.members),
            selectinload(Game.acts).selectinload(Act.scenes),
            selectinload(Game.session0_prompts).selectinload(Session0Prompt.responses),
            selectinload(Game.world_document),
            selectinload(Game.safety_tools),
            selectinload(Game.proposals).selectinload(VoteProposal.votes).selectinload(Vote.voter),
            selectinload(Game.proposals).selectinload(VoteProposal.proposed_by),
            selectinload(Game.proposals).selectinload(VoteProposal.act),
            selectinload(Game.proposals).selectinload(VoteProposal.scene),
            selectinload(Game.proposals).selectinload(VoteProposal.beat),
        )
    )
    return result.scalar_one_or_none()


def _resolve_tension_proposal(proposal: VoteProposal) -> None:
    """Apply plurality vote result to scene.tension_carry_forward and mark proposal approved.

    VoteChoice mapping for tension: yes → +1, suggest_modification → 0, no → -1.
    AI suggestion is used as tiebreaker and default when no votes were cast.
    scene.tension is left untouched — it is the historical record of what tension the scene ran at.
    """
    if proposal.scene is None:
        return
    yes_count = sum(1 for v in proposal.votes if v.choice == VoteChoice.yes)
    suggest_count = sum(1 for v in proposal.votes if v.choice == VoteChoice.suggest_modification)
    no_count = sum(1 for v in proposal.votes if v.choice == VoteChoice.no)
    delta = resolve_tension_vote(yes_count, suggest_count, no_count, proposal.tension_delta or 0)
    proposal.scene.tension_carry_forward = max(1, min(9, proposal.scene.tension + delta))
    proposal.status = ProposalStatus.approved


async def _create_tension_adjustment_proposal(
    scene: Scene,
    game: Game,
    db: AsyncSession,
) -> None:
    """Evaluate tension after scene completion and open a tension_adjustment proposal.

    For single-player games, applies the AI suggestion immediately without a vote.
    AI failure is caught and swallowed — scene completion is never rolled back.
    """
    total_players = len(game.members)

    # Load full scene with beats and characters for AI context assembly
    result = await db.execute(
        select(Scene)
        .where(Scene.id == scene.id)
        .options(
            selectinload(Scene.act),
            selectinload(Scene.beats).selectinload(Beat.events),
            selectinload(Scene.characters_present),
        )
    )
    full_scene = result.scalar_one_or_none()
    if full_scene is None:
        return

    # Build recent scene history: last 3 completed scenes in the same act
    act_in_game = next((a for a in game.acts if a.id == full_scene.act_id), None)
    recent_history: list[tuple[int, str | None]] = []
    if act_in_game is not None:
        completed_prior = sorted(
            [
                s
                for s in act_in_game.scenes
                if s.status == SceneStatus.complete and s.id != scene.id
            ],
            key=lambda s: s.order,
        )[-3:]
        # Find rationale from resolved tension proposals for those scenes
        resolved_tension = {
            p.scene_id: p.ai_rationale
            for p in game.proposals
            if p.proposal_type == ProposalType.tension_adjustment
            and p.status == ProposalStatus.approved
            and p.scene_id is not None
        }
        for s in completed_prior:
            recent_history.append((s.tension, resolved_tension.get(s.id)))

    try:
        delta, rationale = await evaluate_tension_adjustment(
            game,
            full_scene,
            recent_history,
            db=db,
            game_id=game.id,
        )
    except Exception:
        logger.exception("Failed to evaluate tension adjustment for scene %d", scene.id)
        return

    if total_players == 1:
        # Single-player: apply immediately, no vote
        scene.tension_carry_forward = max(1, min(9, scene.tension + delta))
        return

    tension_proposal = VoteProposal(
        game_id=game.id,
        proposal_type=ProposalType.tension_adjustment,
        proposed_by_id=None,
        scene_id=scene.id,
        tension_delta=delta,
        ai_rationale=rationale,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=game.silence_timer_hours),
    )
    db.add(tension_proposal)
    await db.flush()


async def _suggest_character_updates_for_scene(
    scene: Scene,
    game: Game,
    db: AsyncSession,
) -> None:
    """Generate AI character update suggestions for all owned characters after scene completion.

    Runs per-character suggestion in parallel. AI failures are caught per-character
    so one failure does not prevent others from receiving suggestions.
    Scene completion is never rolled back by this function.
    """
    # Load scene with beats for AI context (re-query to get fresh state)
    result = await db.execute(
        select(Scene)
        .where(Scene.id == scene.id)
        .options(
            selectinload(Scene.act),
            selectinload(Scene.beats).selectinload(Beat.events),
            selectinload(Scene.characters_present),
        )
    )
    full_scene = result.scalar_one_or_none()
    if full_scene is None:
        return

    # Only process owned characters (skip NPCs)
    chars_result = await db.execute(
        select(Character).where(
            Character.game_id == game.id,
            Character.owner_id.is_not(None),
        )
    )
    owned_characters = list(chars_result.scalars().all())
    if not owned_characters:
        return

    async def _process_one(character: Character) -> None:
        try:
            suggestions = await _ai_suggest_character_updates(
                game,
                full_scene,
                character,
                db=db,
                game_id=game.id,
            )
        except Exception:
            logger.exception(
                "Failed to generate character update suggestions for scene %d", scene.id
            )
            return

        if not suggestions:
            return

        for category_str, text, reason, beat_ids in suggestions:
            try:
                category = CharacterUpdateCategory(category_str)
            except ValueError:
                continue
            suggestion = CharacterUpdateSuggestion(
                character_id=character.id,
                scene_id=scene.id,
                category=category,
                suggestion_text=text,
                reason=reason,
                referenced_beat_ids=json.dumps(beat_ids) if beat_ids else None,
                status=CharacterUpdateStatus.pending,
            )
            db.add(suggestion)

        await db.flush()

        if character.owner_id is not None:
            await create_notification(
                db,
                user_id=character.owner_id,
                game_id=game.id,
                ntype=NotificationType.character_update_suggested,
                message=(
                    f"The AI has suggestions for {character.name}'s character sheet "
                    f"based on the completed scene."
                ),
                link=f"/games/{game.id}/characters/{character.id}/suggestions",
            )

    await asyncio.gather(*[_process_one(c) for c in owned_characters])


async def _compile_scene_narrative(scene: Scene, game: Game, db: AsyncSession) -> None:
    """Generate and store a prose narrative for a completed scene.

    Skipped when auto_generate_narrative is disabled. AI failures are logged but
    do not roll back scene completion. No separate commit — caller commits.
    """
    if not game.auto_generate_narrative:
        return

    result = await db.execute(
        select(Scene)
        .where(Scene.id == scene.id)
        .options(
            selectinload(Scene.act),
            selectinload(Scene.beats).selectinload(Beat.events),
            selectinload(Scene.characters_present),
        )
    )
    full_scene = result.scalar_one_or_none()
    if full_scene is None:
        return

    try:
        narrative = await _ai_generate_scene_narrative(game, full_scene, db=db, game_id=game.id)
    except Exception:
        logger.exception("Failed to generate scene narrative for scene %d", scene.id)
        return

    full_scene.narrative = narrative


async def create_world_doc_and_proposal(
    game: Game,
    proposer_id: int,
    proposal_type: ProposalType,
    db: AsyncSession,
) -> tuple[WorldDocument, VoteProposal, bool]:
    """Generate world doc, open a proposal, add proposer's implicit yes vote.

    Checks auto-resolution (single-player games approve immediately).

    Args:
        game: Fully loaded game (world_document + proposals + votes eagerly loaded).
        proposer_id: User ID of the player proposing.
        proposal_type: Type of proposal to create.
        db: Async database session.

    Returns:
        (world_doc, proposal, auto_approved) — auto_approved is True when the
        proposer's yes alone meets the threshold (e.g., a 1-player game).
    """
    total_players = len(game.members)

    # Generate (or regenerate) world document content
    content = await _ai_generate_world_document(
        _collect_session0_data(game), db=db, game_id=game.id
    )

    world_doc = game.world_document
    if world_doc is None:
        world_doc = WorldDocument(game_id=game.id, content=content)
        db.add(world_doc)
    else:
        world_doc.content = content

    # Reuse existing open proposal or create a new one
    open_proposal = next((p for p in game.proposals if p.status == ProposalStatus.open), None)
    is_new_proposal = open_proposal is None
    if not is_new_proposal:
        if open_proposal.proposal_type != proposal_type:
            raise HTTPException(
                status_code=409,
                detail="A conflicting open proposal already exists",
            )
        proposal = open_proposal
    else:
        proposal = VoteProposal(
            game_id=game.id,
            proposal_type=proposal_type,
            proposed_by_id=proposer_id,
        )
        db.add(proposal)
        await db.flush()

    # Add proposer's implicit yes vote (idempotent).
    # For a brand-new proposal the votes collection is not yet loaded; use the flag.
    if is_new_proposal:
        existing_vote = None
    else:
        existing_vote = next((v for v in proposal.votes if v.voter_id == proposer_id), None)

    added_yes = False
    if existing_vote is None:
        db.add(
            Vote(
                proposal_id=proposal.id,
                voter_id=proposer_id,
                choice=VoteChoice.yes,
            )
        )
        added_yes = True

    # Compute yes count without relying on the in-memory collection for new proposals.
    if is_new_proposal:
        yes_count = 1 if added_yes else 0
    else:
        yes_count = sum(1 for v in proposal.votes if v.choice == VoteChoice.yes)
        if added_yes:
            yes_count += 1
    auto_approved = is_approved(yes_count, total_players)

    if auto_approved:
        proposal.status = ProposalStatus.approved
        game.status = GameStatus.active

    return world_doc, proposal, auto_approved


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/games/{game_id}/world-document", response_class=HTMLResponse)
async def view_world_document(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the world document and current vote status."""
    game = await _load_game_for_voting(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    # Find the most relevant proposal: open first, then latest approved
    proposal = next((p for p in game.proposals if p.status == ProposalStatus.open), None)
    if proposal is None:
        proposal = next(
            (p for p in reversed(game.proposals) if p.status == ProposalStatus.approved),
            None,
        )

    my_vote = None
    yes_count = no_count = suggest_count = 0
    if proposal is not None:
        my_vote = next((v for v in proposal.votes if v.voter_id == current_user.id), None)
        yes_count = sum(1 for v in proposal.votes if v.choice == VoteChoice.yes)
        no_count = sum(1 for v in proposal.votes if v.choice == VoteChoice.no)
        suggest_count = sum(
            1 for v in proposal.votes if v.choice == VoteChoice.suggest_modification
        )

    total_players = len(game.members)
    threshold = approval_threshold(total_players) if game.status != GameStatus.active else 0
    has_open_proposal = any(p.status == ProposalStatus.open for p in game.proposals)

    return templates.TemplateResponse(
        request,
        "world_document.html",
        {
            "game": game,
            "current_member": current_member,
            "current_user": current_user,
            "world_document": game.world_document,
            "proposal": proposal,
            "my_vote": my_vote,
            "yes_count": yes_count,
            "no_count": no_count,
            "suggest_count": suggest_count,
            "total_players": total_players,
            "threshold": threshold,
            "has_open_proposal": has_open_proposal,
        },
    )


@router.post("/games/{game_id}/proposals/{proposal_id}/vote", response_class=RedirectResponse)
async def cast_vote(
    game_id: int,
    proposal_id: int,
    request: Request,
    choice: str = Form(...),
    suggestion: str = Form(""),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Cast a vote on a proposal. Proposer's implicit yes is already recorded."""
    game = await _load_game_for_voting(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    proposal = next((p for p in game.proposals if p.id == proposal_id), None)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # loo-4ur6: defense-in-depth — ensure proposal belongs to this game
    if proposal.game_id != game_id:
        raise HTTPException(status_code=403, detail="Proposal does not belong to this game")

    if proposal.status != ProposalStatus.open:
        raise HTTPException(status_code=403, detail="This proposal is no longer open")

    try:
        vote_choice = VoteChoice(choice)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid vote choice")

    new_vote = Vote(
        proposal_id=proposal_id,
        voter_id=current_user.id,
        choice=vote_choice,
        suggestion=suggestion.strip() or None,
    )
    proposal.votes.append(new_vote)

    # loo-p1mt: use DB UniqueConstraint to guard against concurrent duplicate votes
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="You have already voted on this proposal")

    # Reset silence timer if a modification is suggested on a beat proposal
    if (
        vote_choice == VoteChoice.suggest_modification
        and proposal.proposal_type == ProposalType.beat_proposal
    ):
        proposal.expires_at = datetime.now(timezone.utc) + timedelta(hours=game.silence_timer_hours)

    total_players = len(game.members)
    yes_count = sum(1 for v in proposal.votes if v.choice == VoteChoice.yes)

    # Tension adjustment: resolve by plurality once all players have voted.
    # Must be checked before is_approved() because "+1 Escalate" maps to VoteChoice.yes,
    # which would cause is_approved() to mark the proposal approved first and skip this block.
    if (
        proposal.proposal_type == ProposalType.tension_adjustment
        and proposal.status == ProposalStatus.open
        and len(proposal.votes) >= total_players
    ):
        _resolve_tension_proposal(proposal)
    elif is_approved(yes_count, total_players):
        proposal.status = ProposalStatus.approved
        if proposal.proposal_type in (ProposalType.world_doc_approval, ProposalType.ready_to_play):
            game.status = GameStatus.active
        elif proposal.proposal_type == ProposalType.act_proposal and proposal.act is not None:
            activate_act(game.acts, proposal.act)
        elif proposal.proposal_type == ProposalType.scene_proposal and proposal.scene is not None:
            act = next((a for a in game.acts if a.id == proposal.scene.act_id), None)
            if act is not None:
                activate_scene(act.scenes, proposal.scene)
        elif proposal.proposal_type == ProposalType.beat_proposal and proposal.beat is not None:
            proposal.beat.status = BeatStatus.canon
            background_tasks.add_task(_scan_beat_for_world_entries, proposal.beat.id, game_id)
            background_tasks.add_task(_scan_beat_for_relationships, proposal.beat.id, game_id)
        elif proposal.proposal_type == ProposalType.scene_complete and proposal.scene is not None:
            proposal.scene.status = SceneStatus.complete
            await _create_tension_adjustment_proposal(proposal.scene, game, db)
            await _suggest_character_updates_for_scene(proposal.scene, game, db)
            await _compile_scene_narrative(proposal.scene, game, db)
        elif proposal.proposal_type == ProposalType.act_complete and proposal.act is not None:
            proposal.act.status = ActStatus.complete
            for scene in proposal.act.scenes:
                if scene.status == SceneStatus.active:
                    scene.status = SceneStatus.complete
            await _compile_act_narrative(proposal.act, game, db)

    await db.commit()

    if proposal.proposal_type == ProposalType.act_proposal:
        return RedirectResponse(url=f"/games/{game_id}/acts", status_code=303)
    if proposal.proposal_type == ProposalType.scene_proposal and proposal.scene is not None:
        return RedirectResponse(
            url=f"/games/{game_id}/acts/{proposal.scene.act_id}/scenes", status_code=303
        )
    if proposal.proposal_type == ProposalType.beat_proposal and proposal.beat is not None:
        beat = proposal.beat
        scene_id = beat.scene_id
        act = next((a for a in game.acts if any(s.id == scene_id for s in a.scenes)), None)
        if act is not None:
            return RedirectResponse(
                url=f"/games/{game_id}/acts/{act.id}/scenes/{scene_id}", status_code=303
            )
    if proposal.proposal_type == ProposalType.tension_adjustment and proposal.scene is not None:
        scene = proposal.scene
        return RedirectResponse(
            url=f"/games/{game_id}/acts/{scene.act_id}/scenes/{scene.id}", status_code=303
        )
    if proposal.proposal_type == ProposalType.scene_complete and proposal.scene is not None:
        scene = proposal.scene
        return RedirectResponse(
            url=f"/games/{game_id}/acts/{scene.act_id}/scenes/{scene.id}", status_code=303
        )
    if proposal.proposal_type == ProposalType.act_complete and proposal.act is not None:
        act = proposal.act
        return RedirectResponse(url=f"/games/{game_id}/acts/{act.id}/scenes", status_code=303)
    return RedirectResponse(url=f"/games/{game_id}/world-document", status_code=303)
