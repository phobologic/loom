---
id: loo-fvoc
status: open
deps: [loo-ofqu]
links: []
created: 2026-02-27T00:05:16Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-82fd
---
# Migrate test_scenes.py to shared fixtures

test_scenes.py is the largest test file (103 tests, 2023 lines) and uses _test_session_factory global. Heaviest win from the migration.

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
  ...  (body, using db directly — it's already an open session)

## Steps
1. Record baseline: time uv run pytest -v tests/test_scenes.py
2. Remove _test_session_factory global and local client fixture
3. Remove now-unused imports
4. Update all test methods that open _test_session_factory sessions (scan thoroughly — 103 tests)
5. Run: time uv run pytest -v tests/test_scenes.py

103 tests. This file will see the biggest absolute time improvement. Include before/after timings as a note on this ticket.

