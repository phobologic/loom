# loom

## Commands

```
# Add project commands here
```

## Browser Testing

Use the `playwright-cli` skill (via `/playwright-cli`) for end-to-end browser testing, UI smoke tests, and verifying rendered HTML behavior.

- Use for auth flows, page navigation, and JS/HTMX interaction testing
- Complements the API-level tests in `tests/` which use FastAPI TestClient
- Start the dev server first: `uv run uvicorn loom.main:app --reload`
- Save screenshots to `tests/e2e/screenshots/` using numbered names (`01-description.png`)
- Screenshots are `.gitignore`d — do not commit them
- Any bugs or regressions found during a playwright session must be filed as a `tk` ticket before ending the session: `tk create "..." -t bug -p <priority> --tags playwright`

## Smoke Test Manifest

`tests/e2e/smoke-manifest.md` is the authoritative list of testable workflows. Run `/smoketest` to execute the full suite against a live dev server.

**When adding a new user-facing workflow, or modifying the behavior of an existing one, as part of any implementation step**, the plan must include updating `smoke-manifest.md` with:
- The workflow name and where it fits in test order (dependencies first)
- Preconditions (what state must exist before the test)
- Actions (what the user does)
- Pass criteria (what a correctly working flow looks like)
- Default failure severity (P0 = blocks everything, P1 = feature broken, P2 = cosmetic)
