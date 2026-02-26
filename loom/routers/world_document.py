"""World document and voting routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.ai.client import generate_world_document as _ai_generate_world_document
from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import (
    Act,
    BeatStatus,
    Game,
    GameMember,
    GameStatus,
    ProposalStatus,
    ProposalType,
    Session0Prompt,
    User,
    Vote,
    VoteChoice,
    VoteProposal,
    WorldDocument,
)
from loom.rendering import templates
from loom.voting import activate_act, activate_scene, approval_threshold, is_approved

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
            selectinload(Game.proposals).selectinload(VoteProposal.votes).selectinload(Vote.voter),
            selectinload(Game.proposals).selectinload(VoteProposal.proposed_by),
            selectinload(Game.proposals).selectinload(VoteProposal.act),
            selectinload(Game.proposals).selectinload(VoteProposal.scene),
            selectinload(Game.proposals).selectinload(VoteProposal.beat),
        )
    )
    return result.scalar_one_or_none()


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
    content = await _ai_generate_world_document(_collect_session0_data(game))

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

    if is_approved(yes_count, total_players):
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
    return RedirectResponse(url=f"/games/{game_id}/world-document", status_code=303)
