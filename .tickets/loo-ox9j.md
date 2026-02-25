---
id: loo-ox9j
status: closed
deps: []
links: []
created: 2026-02-25T02:29:41Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# StaticFiles mount uses relative directory path — breaks when app is started from a different cwd

**File**: loom/main.py | **Line(s)**: 42 | **Description**: app.mount('/static', StaticFiles(directory='loom/static')) and Jinja2Templates(directory='loom/templates') in routers use relative paths. These work when uvicorn is launched from the repo root but will raise RuntimeError if the process working directory differs (e.g. running tests from a subdirectory, Docker WORKDIR set differently, or systemd unit with a different cwd). | **Suggested Fix**: Derive the path relative to __file__ using pathlib: directory=Path(__file__).parent / 'static'.

