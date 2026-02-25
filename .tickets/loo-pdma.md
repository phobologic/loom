---
id: loo-pdma
status: open
deps: []
links: [loo-kicp]
created: 2026-02-25T02:28:58Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:perf]
---
# Repeated boilerplate DB queries across game-scoped route handlers

**File**: loom/routers/games.py
**Line(s)**: 90-101, 210-219, 243-252, 278-290, 304-313
**Description**: Every game-scoped endpoint executes the same pattern: query Game with selectinload(Game.members), check for 404, call _find_membership, check for 403. This is at least one SELECT per request and is duplicated five times. There is no caching or shared dependency injection.

Each request that needs game authorization makes a full round-trip to the database for the game row plus the members collection. If these endpoints are hit in quick succession (e.g., settings page load followed by form submit) the same data is fetched twice.

**Suggested Fix**: Extract a reusable FastAPI dependency that loads the game (with members) and validates membership in one place, similar to how get_current_user is already factored out:

    async def get_game_and_member(
        game_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> tuple[Game, GameMember]:
        result = await db.execute(
            select(Game).where(Game.id == game_id).options(selectinload(Game.members).selectinload(GameMember.user))
        )
        game = result.scalar_one_or_none()
        if game is None:
            raise HTTPException(status_code=404, detail='Game not found')
        member = _find_membership(game, current_user.id)
        if member is None:
            raise HTTPException(status_code=403, detail='You are not a member of this game')
        return game, member

This eliminates the duplicated query code and reduces the chance of inconsistent authorization checks being introduced in future handlers.

