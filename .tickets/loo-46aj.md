---
id: loo-46aj
status: closed
deps: []
links: []
created: 2026-02-25T01:22:40Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 1: Project Scaffolding

Set up the repo, Python project with uv, FastAPI, Jinja2 templating, HTMX, PostgreSQL via docker-compose, SQLAlchemy + Alembic, config management for local/dev/prod environments, basic linting. A 'hello world' page renders in the browser.

**AI Stub Contract (applies from this step forward):** All AI calls throughout Steps 1–22 are stubbed. Stubs must return realistic hardcoded responses — not empty strings or None. Examples: significance classifier stub always returns 'minor'; oracle stub returns 3 hardcoded plausible interpretations; Session 0 synthesis stub returns a paragraph of genre-appropriate placeholder prose.

**Real-Time Updates (applies from Step 13):** Use HTMX polling (hx-trigger='every 5s') on the beat timeline so new beats from other players appear without a manual page reload. Decide on this approach in Step 1 and wire it up in Step 13.

## Acceptance Criteria

### REQ-TECH-001: Technology Stack
*Requirement:* Loom shall be built with the following technology stack.
*Acceptance Criteria:*
- Backend: Python with FastAPI.
- Templating: Jinja2 for server-rendered pages.
- Frontend interactivity: HTMX for dynamic behavior without a JavaScript framework.
- Database: PostgreSQL (AWS Aurora for production, local PostgreSQL for development/testing).
- ORM: SQLAlchemy with Alembic for migrations.
- AI: Anthropic API via abstraction layer (see REQ-AI-001).
- Authentication: OAuth via Google and Discord.

---

### REQ-TECH-004: Local Development
*Requirement:* Loom shall support local development with minimal setup.
*Acceptance Criteria:*
- Developers can run the full application locally with a local PostgreSQL instance.
- A docker-compose or equivalent setup is provided for local dependencies.
- Environment variables or a local configuration file manage settings for different environments.
- Tests can run against a local/test database.

