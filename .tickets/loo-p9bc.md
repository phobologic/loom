---
id: loo-p9bc
status: closed
deps: []
links: [loo-ryzm]
created: 2026-02-25T02:29:27Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:perf]
---
# SQLAlchemy engine created with echo=settings.debug, verbose in production if misconfigured

**File**: loom/database.py
**Line(s)**: 8
**Description**: The engine is created with echo=settings.debug. If debug=True in production (or if the .env is absent and the default value is used), SQLAlchemy will log every SQL statement to stdout. This adds string formatting and I/O overhead on every database operation and can expose query details in logs.

The default in config.py is debug=True, meaning a missing .env file will result in a production deployment with SQL echoing enabled.

**Suggested Fix**: Use a dedicated flag for SQL echo rather than tying it to the generic debug flag, or default debug to False:

    # config.py
    debug: bool = False  # change default
    sql_echo: bool = False  # or a separate flag

    # database.py
    engine = create_async_engine(settings.database_url, echo=settings.sql_echo)


## Notes

**2026-02-25T02:32:34Z**

Duplicate of loo-ryzm
