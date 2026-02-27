---
id: loo-z8yh
status: closed
deps: [loo-ofqu]
links: []
created: 2026-02-27T00:05:11Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-82fd
---
# Migrate test_acts.py to shared fixtures

test_acts.py uses _test_session_factory global for direct DB assertions after HTTP requests. Heavy usage — many tests open DB sessions directly.

## Current pattern
Global _test_session_factory set by local client fixture. Tests call:
  async with _test_session_factory() as db:
      result = await db.execute(...)

## New pattern
Replace with shared client + db fixtures from conftest.py (loo-ofqu).

Tests that use _test_session_factory add db as a fixture parameter. Replace all:
  async with _test_session_factory() as db:
      ...  (body)
With:
  ...  (body, using db directly)

The db fixture is already an open session — no need for the async with wrapper.

## Steps
1. Record baseline: time uv run pytest -v tests/test_acts.py
2. Remove _test_session_factory global and local client fixture  
3. Remove now-unused imports
4. Update test methods (there are many — scan for all async with _test_session_factory)
5. Run: time uv run pytest -v tests/test_acts.py

30 tests in this file. Include before/after timings as a note on this ticket.


## Notes

**2026-02-27T03:44:14Z**

Before: 30 passed in 4.1s wall / 8.4s real. After: 30 passed in 1.8s wall / 5.4s real. ~57% reduction in wall time, ~36% reduction in real time.
