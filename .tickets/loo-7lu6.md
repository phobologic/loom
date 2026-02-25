---
id: loo-7lu6
status: open
deps: []
links: []
created: 2026-02-25T02:29:55Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:readability]
---
# test_games.py test_join_enforces_player_cap uses inline imports mid-test

**File**: tests/test_games.py lines 200-201. The test method test_join_enforces_player_cap imports 'from loom.database import AsyncSessionLocal as ASession' and 'from loom.models import User' inline inside the test body. AsyncSessionLocal and User are already imported at the top of the file (lines 9 and 11). The inline alias ASession is redundant since AsyncSessionLocal is available directly. **Suggested Fix**: Remove the inline imports. The alias 'ASession' provides no clarity benefit and breaks the convention of top-of-file imports used everywhere else in the test suite.

