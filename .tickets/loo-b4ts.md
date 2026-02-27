---
id: loo-b4ts
status: open
deps: [loo-oqhu]
links: []
created: 2026-02-27T05:02:27Z
type: bug
priority: 2
assignee: Michael Barrett
---
# Fix infinite loop risk in _skip_all helpers

Two test helpers use 'while True' with no iteration cap:
- test_session0.py::TestSession0Completion._skip_all (lines 372-383)
- test_world_document.py::_skip_all_prompts (lines 46-62)

If a bug causes prompt advancement to freeze, these loops hang the entire test suite indefinitely with no timeout or useful error message.

Fix: replace 'while True' with a bounded 'for _ in range(N)' (N > max known prompts, e.g. 15). Add an 'else' clause that raises AssertionError('Prompts never reached terminal status') so failures surface clearly.


## Notes

**2026-02-27T05:03:30Z**

IMPLEMENTATION DETAILS:

--- File 1: tests/test_session0.py ---
Find class TestSession0Completion, method _skip_all (around lines 372-383).

Current code:
  async def _skip_all(self, client: AsyncClient, db: AsyncSession, game_id: int) -> None:
      await client.get(f'/games/{game_id}/session0', follow_redirects=False)
      while True:
          prompts = await _get_prompts(db, game_id)
          active = next((p for p in prompts if p.status == PromptStatus.active), None)
          if active is None:
              break
          r = await client.post(
              f'/games/{game_id}/session0/{active.id}/skip', follow_redirects=False
          )
          assert r.status_code == 303

Fixed code:
  async def _skip_all(self, client: AsyncClient, db: AsyncSession, game_id: int) -> None:
      await client.get(f'/games/{game_id}/session0', follow_redirects=False)
      for _ in range(15):  # default session0 has 7 prompts; 15 is a safe upper bound
          prompts = await _get_prompts(db, game_id)
          active = next((p for p in prompts if p.status == PromptStatus.active), None)
          if active is None:
              return
          r = await client.post(
              f'/games/{game_id}/session0/{active.id}/skip', follow_redirects=False
          )
          assert r.status_code == 303
      else:
          raise AssertionError('Session0 prompts never all reached terminal status — possible infinite loop in skip logic')

--- File 2: tests/test_world_document.py ---
Find _skip_all_prompts function around lines 46-62.

Apply the same pattern: replace 'while True' with 'for _ in range(15)', convert 'break' to 'return', add the 'else: raise AssertionError(...)' clause.

VERIFICATION:
- Run 'uv run pytest -v tests/test_session0.py tests/test_world_document.py'
- All tests should pass unchanged (the loop exits normally before hitting the bound)
- Manually verify that 15 is above the max number of session0 prompts by checking loom/models.py or the seed data
