---
id: loo-g5gm
status: closed
deps: []
links: []
created: 2026-02-25T04:50:57Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:readability]
---
# Duplicate client fixture and test helper functions across every new test module

**File**: tests/test_characters.py, tests/test_safety_tools.py, tests/test_session0.py, tests/test_world_document.py
**Line(s)**: fixture at top of each file (approx lines 15-55 in each)
**Description**: Every new test module contains a structurally identical client fixture (in-memory SQLite engine, schema creation, user seeding, dependency override, teardown) and identical _login/_create_game helpers. Any change to the fixture pattern (e.g. adding a new seed user, changing session factory options) must be replicated across all four files.
**Suggested Fix**: Extract the shared fixture and helpers into a conftest.py file at the tests/ level. pytest picks up conftest.py automatically, so the fixtures become available to all test modules without import. The per-module _login and _create_game helpers can stay local if their signatures diverge, but the engine/fixture lifecycle should be shared.

