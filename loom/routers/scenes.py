"""Scene creation and voting routes."""

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
    Character,
    Game,
    GameMember,
    GameStatus,
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
from loom.voting import activate_scene, approval_threshold, is_approved

router = APIRouter()


def _find_membership(game: Game, user_id: int) -> GameMember | None:
    for m in game.members:
        if m.user_id == user_id:
            return m
    return None


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

    if act.status != ActStatus.active:
        raise HTTPException(status_code=403, detail="Scenes can only be viewed for an active act")

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

    if is_approved(1, total_players):
        proposal.status = ProposalStatus.approved
        activate_scene(act.scenes, scene)

    await db.commit()
    return RedirectResponse(url=f"/games/{game_id}/acts/{act_id}/scenes", status_code=303)
