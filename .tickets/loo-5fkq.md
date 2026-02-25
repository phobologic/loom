---
id: loo-5fkq
status: closed
deps: []
links: [loo-02sc]
created: 2026-02-25T02:28:45Z
type: task
priority: 0
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:security]
---
# Hardcoded default session secret key in config

**File**: loom/config.py
**Line(s)**: 10
**Description**: The session_secret_key has a hardcoded insecure default value 'dev-secret-change-me'. If the .env file is absent or the variable is not set in production, the application will use this weak, publicly-known key to sign session cookies. An attacker who knows this default key can forge valid session cookies and impersonate any user.
**Suggested Fix**: Remove the default value entirely so that the application fails loudly on startup if no secret is provided in production. Use a validator (e.g., Pydantic @model_validator or a @field_validator) that raises ValueError when the value matches the insecure placeholder.


## Notes

**2026-02-25T02:39:06Z**

Closing: intentionally deferred. The hardcoded fallback secret is dev-only. Real secret management (env-required, no fallback) belongs with the real auth and deployment hardening work in Step 25. There are no real user sessions at risk until OAuth lands.
