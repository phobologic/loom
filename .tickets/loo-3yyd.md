---
id: loo-3yyd
status: open
deps: [loo-oqhu]
links: []
created: 2026-02-27T05:02:09Z
type: bug
priority: 2
assignee: Michael Barrett
---
# Fix stale ORM state in test_characters.py

The _get_characters helper (test_characters.py:39) is missing a db.expire_all() call before its SELECT. Every other fetch helper in the project calls expire_all() first. Without it, all 12 call sites may return stale identity-map objects after an HTTP request commits a change.

Fix: add db.expire_all() as the first line of _get_characters.

This also resolves the compounding bug in _setup_with_char (lines 231-242), which calls _get_characters immediately after client.post() — if the session cache is stale, chars[0] raises IndexError in all 6 TestEditCharacter tests.


## Notes

**2026-02-27T05:03:03Z**

IMPLEMENTATION DETAILS:

File: tests/test_characters.py, lines 39-43

Current code:
  async def _get_characters(db: AsyncSession, game_id: int) -> list[Character]:
      result = await db.execute(
          select(Character).where(Character.game_id == game_id).order_by(Character.created_at)
      )
      return list(result.scalars().all())

Fixed code:
  async def _get_characters(db: AsyncSession, game_id: int) -> list[Character]:
      db.expire_all()   # <- add this line
      result = await db.execute(
          select(Character).where(Character.game_id == game_id).order_by(Character.created_at)
      )
      return list(result.scalars().all())

CALL SITES AFFECTED (all in test_characters.py):
- TestCreateCharacter: ~line 139, 168, 178, 195, 227
- TestEditCharacter: ~line 249, 254, 275, 284, 313, 322
- _setup_with_char: ~line 241

The _setup_with_char helper (lines 231-242) is the most dangerous: it calls _get_characters immediately after client.post() which creates the character via HTTP. If the session cache is stale (empty), chars[0] raises IndexError and all 6 TestEditCharacter tests fail with a confusing error that looks like the POST failed when it actually succeeded.

VERIFICATION: Run 'uv run pytest -v tests/test_characters.py' before and after. All tests should pass. The fix should make the test suite more reliable, not change any test outcomes (if they were passing before it was because SQLAlchemy happened to miss the cache, not because expire_all is unnecessary).
