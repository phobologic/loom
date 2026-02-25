---
id: loo-6jti
status: closed
deps: []
links: []
created: 2026-02-25T04:51:38Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:readability]
---
# _AuthRedirect is a private implementation detail imported across module boundaries

**File**: loom/dependencies.py (line 13), loom/main.py (line 18)
**Line(s)**: dependencies.py:13, main.py:18
**Description**: _AuthRedirect is named with a leading underscore signalling it is private, yet it is explicitly imported into main.py to register the exception handler. This is a mild naming inconsistency — the underscore convention implies callers outside the module should not touch it, but main.py must do exactly that. The class is also undiscoverable to future developers who might wonder where auth redirect handling lives.
**Suggested Fix**: Either rename the class to AuthRedirect (removing the privacy signal since it is part of the public contract between dependencies.py and main.py), or add a comment at the definition site explaining that main.py is the intended and only consumer.

