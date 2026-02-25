---
id: loo-02sc
status: closed
deps: []
links: [loo-5fkq]
created: 2026-02-25T02:29:47Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# session_secret_key has an insecure hardcoded default that will be used silently in production

**File**: loom/config.py | **Line(s)**: 10 | **Description**: session_secret_key defaults to 'dev-secret-change-me'. If an operator deploys without setting this env var, all sessions are signed with a public well-known key. Any attacker who knows the default can forge session cookies and impersonate any user. Pydantic-settings makes it easy to require the field with no default. | **Suggested Fix**: Remove the default value so Pydantic raises a validation error on startup if SESSION_SECRET_KEY is not set. Apply this only when environment \!= 'local', or always require it and document how to set it in .env.example.


## Notes

**2026-02-25T02:32:25Z**

Duplicate of loo-5fkq
