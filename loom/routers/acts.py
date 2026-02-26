"""Act creation and voting routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from loom.database import get_db
from loom.dependencies import get_current_user
from loom.models import (
    Act,
    ActStatus,
    Game,
    GameMember,
    GameStatus,
    NotificationType,
    ProposalStatus,
    ProposalType,
    SceneStatus,
    User,
    Vote,
    VoteChoice,
    VoteProposal,
)
from loom.notifications import notify_game_members
from loom.rendering import templates
from loom.voting import activate_act, approval_threshold, is_approved

router = APIRouter()


def _find_membership(game: Game, user_id: int) -> GameMember | None:
    for m in game.members:
        if m.user_id == user_id:
            return m
    return None


async def _load_game_for_acts(game_id: int, db: AsyncSession) -> Game | None:
    result = await db.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(
            selectinload(Game.members),
            selectinload(Game.acts).selectinload(Act.scenes),
            selectinload(Game.proposals).selectinload(VoteProposal.votes).selectinload(Vote.voter),
            selectinload(Game.proposals).selectinload(VoteProposal.proposed_by),
            selectinload(Game.proposals).selectinload(VoteProposal.act),
        )
    )
    return result.scalar_one_or_none()


@router.get("/games/{game_id}/acts", response_class=HTMLResponse)
async def acts_view(
    game_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Show the acts list, any pending act proposal with voting, and the proposal form."""
    game = await _load_game_for_acts(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    acts = sorted(game.acts, key=lambda a: a.order)

    open_proposal = next(
        (
            p
            for p in game.proposals
            if p.status == ProposalStatus.open and p.proposal_type == ProposalType.act_proposal
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

    return templates.TemplateResponse(
        request,
        "acts.html",
        {
            "game": game,
            "current_member": current_member,
            "current_user": current_user,
            "acts": acts,
            "open_proposal": open_proposal,
            "my_vote": my_vote,
            "yes_count": yes_count,
            "no_count": no_count,
            "suggest_count": suggest_count,
            "total_players": total_players,
            "threshold": threshold,
        },
    )


@router.post("/games/{game_id}/acts", response_class=RedirectResponse)
async def propose_act(
    game_id: int,
    request: Request,
    title: str = Form(""),
    guiding_question: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Propose a new act. Goes through the standard voting flow."""
    game = await _load_game_for_acts(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    if game.status != GameStatus.active:
        raise HTTPException(status_code=403, detail="Game must be active to propose an act")

    if not guiding_question.strip():
        raise HTTPException(status_code=422, detail="Guiding question is required")

    has_open = any(
        p.status == ProposalStatus.open and p.proposal_type == ProposalType.act_proposal
        for p in game.proposals
    )
    if has_open:
        raise HTTPException(status_code=409, detail="An act proposal is already pending")

    next_order = max((a.order for a in game.acts), default=0) + 1

    act = Act(
        game_id=game.id,
        title=title.strip() or None,
        guiding_question=guiding_question.strip(),
        status=ActStatus.proposed,
        order=next_order,
    )
    db.add(act)
    await db.flush()

    total_players = len(game.members)
    proposal = VoteProposal(
        game_id=game.id,
        proposal_type=ProposalType.act_proposal,
        proposed_by_id=current_user.id,
        act_id=act.id,
    )
    db.add(proposal)
    await db.flush()

    db.add(Vote(proposal_id=proposal.id, voter_id=current_user.id, choice=VoteChoice.yes))

    auto_approved = is_approved(1, total_players)
    if auto_approved:
        proposal.status = ProposalStatus.approved
        activate_act(game.acts, act)

    link = f"/games/{game_id}/acts"
    label = act.guiding_question[:60]
    if auto_approved:
        await notify_game_members(
            db,
            game,
            NotificationType.act_proposed,
            f'Act approved: "{label}"',
            link=link,
        )
    else:
        await notify_game_members(
            db,
            game,
            NotificationType.vote_required,
            f'Vote needed: act proposal "{label}"',
            link=link,
            exclude_user_id=current_user.id,
        )

    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}/acts", status_code=303)


@router.post("/games/{game_id}/acts/{act_id}/complete", response_class=RedirectResponse)
async def propose_act_complete(
    game_id: int,
    act_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Propose completing the current act. Goes through the standard voting flow."""
    game = await _load_game_for_acts(game_id, db)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    current_member = _find_membership(game, current_user.id)
    if current_member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this game")

    act = next((a for a in game.acts if a.id == act_id), None)
    if act is None:
        raise HTTPException(status_code=404, detail="Act not found")

    if act.status != ActStatus.active:
        raise HTTPException(status_code=403, detail="Act must be active to propose completion")

    has_open = any(
        p.status == ProposalStatus.open
        and p.proposal_type == ProposalType.act_complete
        and p.act_id == act.id
        for p in game.proposals
    )
    if has_open:
        raise HTTPException(status_code=409, detail="An act completion proposal is already pending")

    total_players = len(game.members)
    proposal = VoteProposal(
        game_id=game.id,
        proposal_type=ProposalType.act_complete,
        proposed_by_id=current_user.id,
        act_id=act.id,
    )
    db.add(proposal)
    await db.flush()

    db.add(Vote(proposal_id=proposal.id, voter_id=current_user.id, choice=VoteChoice.yes))

    auto_approved = is_approved(1, total_players)
    if auto_approved:
        proposal.status = ProposalStatus.approved
        act.status = ActStatus.complete
        for scene in act.scenes:
            if scene.status == SceneStatus.active:
                scene.status = SceneStatus.complete

    link = f"/games/{game_id}/acts/{act_id}/scenes"
    label = act.guiding_question[:60]
    if auto_approved:
        await notify_game_members(
            db,
            game,
            NotificationType.act_proposed,
            f'Act completed: "{label}"',
            link=link,
        )
    else:
        await notify_game_members(
            db,
            game,
            NotificationType.vote_required,
            f'Vote needed: complete act "{label}"',
            link=link,
            exclude_user_id=current_user.id,
        )

    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}/acts/{act_id}/scenes", status_code=303)
