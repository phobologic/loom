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
