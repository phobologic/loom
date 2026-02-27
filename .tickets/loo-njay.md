---
id: loo-njay
status: open
deps: [loo-xzt9]
links: []
created: 2026-02-27T05:02:50Z
type: chore
priority: 3
assignee: Michael Barrett
---
# Consolidate parameterized test helpers into conftest.py (Phase 2)

Several helpers exist in multiple files with minor signature variations. Consolidate into conftest.py with parameterization:

1. _create_game(client, name='Test Game', pitch='') — 5 files; some lack 'pitch' param, one defaults to 'A pitch'. Unify with both params.

2. _create_active_game(client, db, extra_members=None, game_name='Test Game') — 7 files, two variants:
   - Simple (4 files): single-player, calls propose-ready route
   - Complex (3 files): multi-player, switches to direct DB activation
   A single function with 'extra_members: list[int] | None = None' covers both cases.

3. _activate_game(db, game_id) — only in test_characters.py but useful to share. Direct DB game status mutation.

4. _create_active_scene(db, game_id) -> tuple[int, int] — 5 files with near-identical implementations (creates Act + Scene, returns act_id, scene_id). The complex variant in test_notifications.py (adds character assignment) can stay local.

Steps:
1. Add unified versions to conftest.py.
2. Remove local definitions from each file.
3. Update call sites where signatures differ.
4. Run full test suite.

Depends on Phase 1 ticket (loo-xzt9) being done first to avoid conflicts.


## Notes

**2026-02-27T05:04:22Z**

IMPLEMENTATION DETAILS:

This ticket builds on Phase 1 (loo-xzt9). Complete that first so _login and _add_member are already in conftest.py.

--- 1. _create_game ---
Appears in: test_games.py:19, test_characters.py:17, test_session0.py:27, test_safety_tools.py:25, test_world_document.py:31

Variations between files:
- test_characters.py and test_safety_tools.py: only take 'name' param, no 'pitch'
- test_world_document.py: uses pitch='A pitch' as default
- test_games.py and test_session0.py: pitch='' default

Canonical implementation for conftest.py:
  async def _create_game(client: AsyncClient, name: str = 'Test Game', pitch: str = '') -> int:
      '''Create a game as the currently logged-in user; return game id.'''
      r = await client.post('/games', data={'name': name, 'pitch': pitch}, follow_redirects=False)
      assert r.status_code == 303
      return int(r.headers['location'].rsplit('/', 1)[-1])

Call sites to update: any local calls that pass keyword args may need review, but most call it as _create_game(client) with no args, which is compatible.

--- 2. _create_active_game ---
Appears in: test_acts.py:30, test_scenes.py (similar), test_character_suggestions.py:44, test_oracles.py:34, test_fortune_roll.py:99, test_safety_tools.py (inline), test_world_document.py (inline)

Two variants exist:
A) Simple (test_character_suggestions.py, test_oracles.py, test_fortune_roll.py):
   - Single player only
   - Calls propose-ready route to activate

B) Full (test_acts.py, test_scenes.py):
   - Supports extra_members list
   - Single-player: uses propose-ready route
   - Multi-player: sets game.status = GameStatus.active directly in DB

Canonical unified implementation:
  async def _create_active_game(
      client: AsyncClient,
      db: AsyncSession,
      extra_members: list[int] | None = None,
      game_name: str = 'Test Game',
  ) -> int:
      '''Create a game, optionally add extra members, and activate it. Returns game_id.'''
      await _login(client, 1)
      game_id = await _create_game(client, name=game_name, pitch='A pitch')
      if extra_members:
          for uid in extra_members:
              db.add(GameMember(game_id=game_id, user_id=uid, role=MemberRole.player))
          await db.commit()
          db.expire_all()
          result = await db.execute(select(Game).where(Game.id == game_id))
          game = result.scalar_one()
          game.status = GameStatus.active
          await db.commit()
      else:
          await client.post(f'/games/{game_id}/session0/propose-ready', follow_redirects=False)
      return game_id

Imports needed: from loom.models import GameMember, MemberRole, Game, GameStatus

NOTE: Some test files call _create_active_game without logging in first (they rely on it logging in as user 1 internally). The canonical version calls _login(client, 1) — make sure call sites don't double-login before calling it.

--- 3. _activate_game ---
Currently only in test_characters.py:31.

  async def _activate_game(db: AsyncSession, game_id: int) -> None:
      '''Set game status to active directly in DB, bypassing session0 flow.'''
      result = await db.execute(select(Game).where(Game.id == game_id))
      game = result.scalar_one()
      game.status = GameStatus.active
      await db.commit()

Move to conftest.py. Also used internally by _create_active_game above.

--- 4. _create_active_scene ---
Appears in: test_character_suggestions.py:69, test_oracles.py:44, test_fortune_roll.py:109, test_scenes.py, test_acts.py, test_notifications.py:59 (complex variant — keep local)

Canonical base implementation (handles the 5 simple cases):
  async def _create_active_scene(db: AsyncSession, game_id: int) -> tuple[int, int]:
      '''Create an active Act and an active Scene. Returns (act_id, scene_id).'''
      act = Act(game_id=game_id, guiding_question='What lurks here?', status=ActStatus.active, order=1)
      db.add(act)
      await db.flush()
      scene = Scene(
          act_id=act.id,
          guiding_question='What happens next?',
          status=SceneStatus.active,
          order=1,
          tension=5,
      )
      db.add(scene)
      await db.commit()
      return act.id, scene.id

Imports needed: from loom.models import Act, ActStatus, Scene, SceneStatus

The variant in test_notifications.py also creates a Character and assigns it to the scene — that file should keep its own more complex helper or call _create_active_scene and then add the character.

--- REMOVAL STEPS ---
1. Add all four helpers to conftest.py (after Phase 1 helpers).
2. For each test file: delete local definitions, update imports.
3. Check call sites where game_name or extra_members differ from defaults.
4. Run 'uv run pytest -q --tb=short' after each file to catch issues incrementally.

VERIFICATION: Full suite should pass. No test logic changes — only helper consolidation.
