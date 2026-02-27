---
id: loo-xzt9
status: open
deps: [loo-oqhu]
links: []
created: 2026-02-27T05:02:41Z
type: chore
priority: 3
assignee: Michael Barrett
---
# Consolidate identical test helpers into conftest.py (Phase 1)

Five helper functions are defined identically in multiple test files and can be moved to conftest.py with zero changes:

| Helper | Files | ~LOC saved |
|--------|-------|------------|
| _login(client, user_id) | 11 files | 33 |
| _add_member(db, game_id, user_id, role) | 5 files | 25 |
| _get_proposals(db, game_id) | 4 files | 16 |
| _get_votes(db, proposal_id) | 4 files | 16 |
| _get_game(db, game_id) | 2 files | 8 |

Steps:
1. Add each function to conftest.py (at module level, not as fixtures).
2. Remove the local definitions from each test file.
3. Update imports in each test file as needed.
4. Run the full test suite to confirm nothing broke.

This is pure removal of duplication — no logic changes.


## Notes

**2026-02-27T05:03:57Z**

IMPLEMENTATION DETAILS:

Add each function to tests/conftest.py at module level (NOT as pytest fixtures — these take client/db as arguments and are called directly by tests). Put them after the existing fixtures, in a clearly marked section like '# --- Shared test helpers ---'.

--- 1. _login ---
Appears in: test_games.py:14, test_acts.py:26, test_scenes.py:35, test_characters.py:13, test_character_suggestions.py:40, test_oracles.py:30, test_fortune_roll.py:95, test_session0.py:22, test_safety_tools.py:21, test_world_document.py:27, test_notifications.py:30

Canonical implementation:
  async def _login(client: AsyncClient, user_id: int) -> None:
      await client.post('/dev/login', data={'user_id': str(user_id)}, follow_redirects=False)

--- 2. _add_member ---
Appears in: test_characters.py:24, test_session0.py:37, test_safety_tools.py:32, test_world_document.py:39

Canonical implementation:
  async def _add_member(
      db: AsyncSession, game_id: int, user_id: int, role: MemberRole = MemberRole.player
  ) -> None:
      db.add(GameMember(game_id=game_id, user_id=user_id, role=role))
      await db.commit()

Imports needed: from loom.models import GameMember, MemberRole

--- 3. _get_proposals ---
Appears in: test_acts.py:66, test_scenes.py (similar), test_world_document.py, test_notifications.py

Canonical implementation:
  async def _get_proposals(db: AsyncSession, game_id: int) -> list[VoteProposal]:
      db.expire_all()
      result = await db.execute(select(VoteProposal).where(VoteProposal.game_id == game_id))
      return list(result.scalars().all())

Imports needed: from loom.models import VoteProposal

--- 4. _get_votes ---
Appears in: test_acts.py:72, test_scenes.py, test_world_document.py, test_notifications.py (similar)

Canonical implementation:
  async def _get_votes(db: AsyncSession, proposal_id: int) -> list[Vote]:
      db.expire_all()
      result = await db.execute(select(Vote).where(Vote.proposal_id == proposal_id))
      return list(result.scalars().all())

Imports needed: from loom.models import Vote

--- 5. _get_game ---
Appears in: test_acts.py:78, test_world_document.py (same)

Canonical implementation:
  async def _get_game(db: AsyncSession, game_id: int) -> Game:
      db.expire_all()
      result = await db.execute(select(Game).where(Game.id == game_id))
      return result.scalar_one()

Imports needed: from loom.models import Game

--- REMOVAL STEPS ---
After adding to conftest.py:
1. In each listed test file, delete the local function definition.
2. Remove any imports that were only used by the deleted function.
3. Do NOT add an explicit import of these helpers in the test files — conftest.py functions are automatically available in the same package.
4. Run 'uv run pytest -q --tb=short' to confirm nothing broke.

VERIFICATION: Full suite should pass with no changes to test logic.
