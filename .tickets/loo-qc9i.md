---
id: loo-qc9i
status: closed
deps: []
links: []
created: 2026-02-25T04:52:16Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# Global mutable _test_session_factory in test files is unsafe under parallel test runs

**File**: tests/test_characters.py:70, tests/test_games.py:424, tests/test_safety_tools.py:671, tests/test_session0.py (similar pattern)
**Line(s)**: (see above)
**Description**: Each test module declares a module-level global _test_session_factory that is set inside the client fixture using a global statement. The comment 'safe for serial test execution' acknowledges the risk. If tests are ever run with pytest-xdist or any parallel runner, two concurrent tests in the same module would share and mutate the same global, causing one test's database session to be replaced by another's mid-test. This is a latent concurrency hazard that will produce hard-to-diagnose flakiness.
**Suggested Fix**: Pass the session factory through the fixture itself or via a separate fixture that is function-scoped. Avoid global state in test modules. For example, use a fixture that yields (client, session_factory) as a tuple, or inject the factory as a separate fixture argument.

