"""Tests for oracle invocation routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from loom.models import (
    Act,
    ActStatus,
    Beat,
    BeatStatus,
    Event,
    EventType,
    GameMember,
    MemberRole,
    OracleComment,
    OracleInterpretationVote,
    OracleType,
    ProposalType,
    Scene,
    SceneStatus,
    VoteProposal,
)


async def _login(client: AsyncClient, user_id: int) -> None:
    await client.post("/dev/login", data={"user_id": str(user_id)}, follow_redirects=False)


async def _create_active_game(client: AsyncClient) -> int:
    await _login(client, 1)
    r = await client.post(
        "/games", data={"name": "Test Game", "pitch": "A pitch"}, follow_redirects=False
    )
    game_id = int(r.headers["location"].rsplit("/", 1)[-1])
    await client.post(f"/games/{game_id}/session0/propose-ready", follow_redirects=False)
    return game_id


async def _create_active_scene(db: AsyncSession, game_id: int) -> tuple[int, int]:
    """Insert an active act and active scene, return (act_id, scene_id)."""
    act = Act(
        game_id=game_id,
        guiding_question="What is at stake?",
        status=ActStatus.active,
        order=1,
    )
    db.add(act)
    await db.flush()

    scene = Scene(
        act_id=act.id,
        guiding_question="What happens next?",
        status=SceneStatus.active,
        order=1,
    )
    db.add(scene)
    await db.commit()
    return act.id, scene.id


@pytest.mark.asyncio
async def test_oracle_get_shows_word_pair(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(db, game_id)

    await _login(client, 1)
    r = await client.get(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
        follow_redirects=False,
    )
    assert r.status_code == 200
    body = r.text
    assert "word_action" in body
    assert "word_descriptor" in body
    assert "Invoke Oracle" in body
    assert "Re-roll" in body


@pytest.mark.asyncio
async def test_oracle_post_creates_beat_and_event(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(db, game_id)

    await _login(client, 1)
    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
        data={
            "question": "Will the alliance hold?",
            "word_action": "betray",
            "word_descriptor": "trust",
            "beat_significance": "minor",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    db.expire_all()
    result = await db.execute(
        select(Beat).where(Beat.scene_id == scene_id).options(selectinload(Beat.events))
    )
    beats = result.scalars().all()
    assert len(beats) == 1
    beat = beats[0]
    assert beat.status == BeatStatus.canon

    assert len(beat.events) == 1
    event = beat.events[0]
    assert event.type == EventType.oracle
    assert event.oracle_query == "Will the alliance hold?"
    assert event.word_seed_action == "betray"
    assert event.word_seed_descriptor == "trust"
    assert len(event.interpretations) == 3


@pytest.mark.asyncio
async def test_oracle_post_requires_active_scene(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)

    act = Act(
        game_id=game_id,
        guiding_question="Q",
        status=ActStatus.active,
        order=1,
    )
    db.add(act)
    await db.flush()
    scene = Scene(
        act_id=act.id,
        guiding_question="Q",
        status=SceneStatus.proposed,
        order=1,
    )
    db.add(scene)
    await db.commit()
    act_id, scene_id = act.id, scene.id

    await _login(client, 1)
    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
        data={
            "question": "What lies ahead?",
            "word_action": "reveal",
            "word_descriptor": "shadow",
        },
        follow_redirects=False,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_oracle_post_requires_question(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(db, game_id)

    await _login(client, 1)
    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
        data={
            "question": "   ",
            "word_action": "reveal",
            "word_descriptor": "shadow",
        },
        follow_redirects=False,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_oracle_post_major_creates_proposal(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(db, game_id)

    await _login(client, 1)
    r = await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
        data={
            "question": "What is the cost?",
            "word_action": "sacrifice",
            "word_descriptor": "legacy",
            "beat_significance": "major",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    db.expire_all()
    result = await db.execute(
        select(VoteProposal).where(
            VoteProposal.proposal_type == ProposalType.beat_proposal,
            VoteProposal.game_id == game_id,
        )
    )
    proposals = result.scalars().all()
    assert len(proposals) == 1


async def _invoke_oracle(
    client: AsyncClient,
    db: AsyncSession,
    game_id: int,
    act_id: int,
    scene_id: int,
    oracle_type: str = "world",
) -> int:
    """Helper: invoke oracle and return the created event_id."""
    await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
        data={
            "question": "What does fate hold?",
            "word_action": "reveal",
            "word_descriptor": "shadow",
            "beat_significance": "minor",
            "oracle_type": oracle_type,
        },
        follow_redirects=False,
    )
    db.expire_all()
    result = await db.execute(
        select(Event)
        .join(Beat, Event.beat_id == Beat.id)
        .where(Event.type == EventType.oracle, Beat.scene_id == scene_id)
        .options(selectinload(Event.beat))
    )
    event = result.scalars().first()
    assert event is not None
    return event.id


@pytest.mark.asyncio
async def test_oracle_post_stores_oracle_type(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(db, game_id)

    await _login(client, 1)
    await client.post(
        f"/games/{game_id}/acts/{act_id}/scenes/{scene_id}/oracle",
        data={
            "question": "Personal question",
            "word_action": "seek",
            "word_descriptor": "truth",
            "beat_significance": "minor",
            "oracle_type": "personal",
        },
        follow_redirects=False,
    )

    db.expire_all()
    result = await db.execute(
        select(Event)
        .join(Beat, Event.beat_id == Beat.id)
        .where(Event.type == EventType.oracle, Beat.scene_id == scene_id)
    )
    event = result.scalar_one()
    assert event.oracle_type == OracleType.personal.value
    assert event.oracle_selected_interpretation is None


@pytest.mark.asyncio
async def test_vote_on_interpretation(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(db, game_id)

    await _login(client, 1)
    event_id = await _invoke_oracle(client, db, game_id, act_id, scene_id)

    r = await client.post(
        f"/games/{game_id}/oracle/events/{event_id}/vote",
        data={"interpretation_index": "0"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    db.expire_all()
    result = await db.execute(
        select(OracleInterpretationVote).where(OracleInterpretationVote.event_id == event_id)
    )
    votes = result.scalars().all()
    assert len(votes) == 1
    assert votes[0].interpretation_index == 0


@pytest.mark.asyncio
async def test_vote_custom_alternative(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(db, game_id)

    await _login(client, 1)
    event_id = await _invoke_oracle(client, db, game_id, act_id, scene_id)

    r = await client.post(
        f"/games/{game_id}/oracle/events/{event_id}/vote",
        data={"interpretation_index": "-1", "alternative_text": "My custom interpretation"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    db.expire_all()
    result = await db.execute(
        select(OracleInterpretationVote).where(OracleInterpretationVote.event_id == event_id)
    )
    vote = result.scalar_one()
    assert vote.interpretation_index == -1
    assert vote.alternative_text == "My custom interpretation"


@pytest.mark.asyncio
async def test_duplicate_vote_rejected(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(db, game_id)

    await _login(client, 1)
    event_id = await _invoke_oracle(client, db, game_id, act_id, scene_id)

    await client.post(
        f"/games/{game_id}/oracle/events/{event_id}/vote",
        data={"interpretation_index": "0"},
        follow_redirects=False,
    )
    r = await client.post(
        f"/games/{game_id}/oracle/events/{event_id}/vote",
        data={"interpretation_index": "1"},
        follow_redirects=False,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_comment_on_oracle(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(db, game_id)

    await _login(client, 1)
    event_id = await _invoke_oracle(client, db, game_id, act_id, scene_id)

    r = await client.post(
        f"/games/{game_id}/oracle/events/{event_id}/comment",
        data={"text": "I think option 2 fits best"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    db.expire_all()
    result = await db.execute(select(OracleComment).where(OracleComment.event_id == event_id))
    comments = result.scalars().all()
    assert len(comments) == 1
    assert comments[0].text == "I think option 2 fits best"


@pytest.mark.asyncio
async def test_invoker_selects_interpretation(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(db, game_id)

    await _login(client, 1)
    event_id = await _invoke_oracle(client, db, game_id, act_id, scene_id)

    r = await client.post(
        f"/games/{game_id}/oracle/events/{event_id}/select",
        data={"interpretation_index": "1"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    db.expire_all()
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one()
    assert event.oracle_selected_interpretation is not None


@pytest.mark.asyncio
async def test_non_invoker_cannot_select(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(db, game_id)

    # User 1 invokes; user 2 tries to select
    await _login(client, 1)
    event_id = await _invoke_oracle(client, db, game_id, act_id, scene_id)

    # Add user 2 (Bob) to game so the membership check passes
    db.add(GameMember(game_id=game_id, user_id=2, role=MemberRole.player))
    await db.commit()

    await _login(client, 2)
    r = await client.post(
        f"/games/{game_id}/oracle/events/{event_id}/select",
        data={"interpretation_index": "0"},
        follow_redirects=False,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_cannot_vote_after_selection(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(db, game_id)

    await _login(client, 1)
    event_id = await _invoke_oracle(client, db, game_id, act_id, scene_id)

    # Invoker selects
    await client.post(
        f"/games/{game_id}/oracle/events/{event_id}/select",
        data={"interpretation_index": "0"},
        follow_redirects=False,
    )

    # Voting after selection should fail
    r = await client.post(
        f"/games/{game_id}/oracle/events/{event_id}/vote",
        data={"interpretation_index": "1"},
        follow_redirects=False,
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_tiebreak_selects_from_votes(client: AsyncClient, db: AsyncSession) -> None:
    game_id = await _create_active_game(client)
    act_id, scene_id = await _create_active_scene(db, game_id)

    await _login(client, 1)
    event_id = await _invoke_oracle(client, db, game_id, act_id, scene_id)

    # Cast a vote for interpretation 2
    await client.post(
        f"/games/{game_id}/oracle/events/{event_id}/vote",
        data={"interpretation_index": "2"},
        follow_redirects=False,
    )

    # Invoker uses tie-breaking to resolve
    r = await client.post(
        f"/games/{game_id}/oracle/events/{event_id}/select",
        data={"interpretation_index": "-2"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    db.expire_all()
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one()
    # Should have selected interpretation #2 (index 2)
    assert event.oracle_selected_interpretation is not None
