---
id: loo-k309
status: open
deps: [loo-oqhu]
links: []
created: 2026-02-27T05:02:34Z
type: chore
priority: 3
assignee: Michael Barrett
---
# Remove async_client fixture footgun from conftest

The async_client fixture in conftest.py creates a plain AsyncClient with no DB override wiring. It is not connected to the shared transaction/rollback mechanism. Any test that uses it and hits a DB-backed route will bypass all isolation guarantees and potentially reach the real production get_db.

Currently only test_hello.py uses it (for a DB-free route), but the fixture is a trap waiting for the next developer.

Fix:
1. Delete the async_client fixture from conftest.py.
2. Migrate test_hello.py to use the standard 'client' fixture instead.

Also investigate whether the notification mark-read endpoints intentionally return 302 (found in test_notifications.py:213,245 assertions) vs the 303 used by every other action endpoint — confirm and document or fix.


## Notes

**2026-02-27T05:03:42Z**

IMPLEMENTATION DETAILS:

--- Part 1: Remove async_client fixture ---

In tests/conftest.py, find the async_client fixture (around line 191). It looks like:

  @pytest.fixture
  async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
      async with AsyncClient(app=app, base_url='http://test') as c:
          yield c

This fixture has NO db_conn wiring and NO dependency_overrides setup. It is not connected to the per-test transaction rollback mechanism.

Action:
1. Delete the async_client fixture entirely from conftest.py.
2. Open tests/test_hello.py — it uses async_client. Replace it with 'client'.
   The test probably looks like:
     async def test_hello_world(async_client: AsyncClient) -> None:
         r = await async_client.get('/')
         assert r.status_code == 200
         assert 'Loom' in r.text
   Change to:
     async def test_hello_world(client: AsyncClient) -> None:
         r = await client.get('/')
         assert r.status_code == 200
         assert 'Loom' in r.text
   The '/' route does not require auth, so the shared client fixture works fine.

--- Part 2: Investigate 302 vs 303 on notification mark-read routes ---

In tests/test_notifications.py, around lines 213 and 245, there are assertions:
  assert r.status_code == 302

All other action endpoints in the codebase use 303 See Other. Check:
  loom/routers/notifications.py — find the mark-read and mark-all-read route handlers.

If they use 'return RedirectResponse(url=..., status_code=302)' that is likely an oversight — change to status_code=303 and update the test assertions.
If they use 'return RedirectResponse(url=...)' with no status_code, the default is 307, and the tests are wrong.
If the 302 is intentional for some reason, add a comment in the route explaining why.

VERIFICATION:
- Run 'uv run pytest -v tests/test_hello.py tests/test_notifications.py'
- Both should pass after changes
