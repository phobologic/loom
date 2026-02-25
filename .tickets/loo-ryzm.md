---
id: loo-ryzm
status: closed
deps: []
links: [loo-p9bc]
created: 2026-02-25T02:29:13Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:security]
---
# SQL echo enabled unconditionally via debug flag default

**File**: loom/config.py, loom/database.py | **Line(s)**: config.py:9, database.py:8 | **Description**: debug defaults to True in Settings, and database.py passes echo=settings.debug to create_async_engine. In production this causes all SQL statements (including those containing user data) to be logged to stdout/stderr, potentially leaking sensitive information to log aggregation systems or anyone with log access. | **Suggested Fix**: Default debug to False. In production deployments ensure DEBUG is explicitly set to false via environment variable. Consider separating SQL echo from the general debug flag.


## Notes

**2026-02-25T02:39:25Z**

Closing: intentionally deferred. debug=True and SQL echo are desired dev-environment behaviors at this stage — they make it easy to see what queries are being issued. Switch to debug=False default before any production deployment.
