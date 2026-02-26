# Loom

Async-first collaborative GM-less tabletop roleplaying.

Loom is a web application for 2–5 players who want to run a collaborative
fiction together without a dedicated Game Master. All players share narrative
authority equally. AI serves as a creative assistant — generating oracle
interpretations, classifying beat significance, expanding shorthand into
prose, and maintaining the world document — but never makes decisions for
the players.

## Design philosophy

- **Async-first** — every interaction is designed for players who check in
  at different times throughout the day. Synchronous play is possible but
  not the primary mode.
- **Silence is consent** — if no one objects within a configurable window,
  proposed content becomes canon. Async games don't stall.
- **Player authority** — the player who acts gets final say on their own
  beats, informed by group input and AI suggestions.
- **Bullets over prose** — quick shorthand is always acceptable; the AI can
  expand it later.

## Features

- **Session 0 wizard** — structured prompts for genre, tone, setting,
  tension, and themes, with AI-synthesized world document generation.
- **Safety tools** — lines and veils, editable by any player at any time.
- **Beat timeline** — chronological narrative feed with HTMX live polling.
  Supports narrative, OOC, and roll events in a single beat.
- **Dice rolling** — standard notation parsing (`2d6`, `d20+3`, etc.),
  server-side execution, result inline in the timeline.
- **Significance voting** — AI suggests major/minor; player accepts or
  overrides. Major beats enter a voting flow with configurable silence timer.
- **Oracle** — word-seed-driven interpretations; players discuss, vote, and
  weave the chosen interpretation into a beat.
- **Fortune Roll** — yes/no oracle with player-set odds and tension modifier.
- **Word seed tables** — built-in general and genre tables; custom words
  supported.
- **In-app notifications** — unread counts and mark-as-read for all game
  events.
- **AI integration** — Anthropic Claude for oracle, Session 0 synthesis,
  world document, and beat significance.
- **OAuth auth** — Google and Discord sign-in.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.13, FastAPI |
| Templates | Jinja2 + HTMX |
| ORM / migrations | SQLAlchemy (async) + Alembic |
| Database | SQLite (dev) / any SQLAlchemy-compatible DB |
| AI | Anthropic API |
| Auth | Authlib (OAuth2) |
| Package manager | uv |

## Development setup

```bash
# 1. Install dependencies
uv sync

# 2. Run database migrations
uv run alembic upgrade head

# 3. Start the dev server
uv run fastapi dev loom/main.py
```

The app starts at `http://localhost:8000`. In development mode a list of
test users is available at `/dev/login` — click any name to get a session.

### Running tests

```bash
uv run pytest -q --tb=short
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

## License

MIT — see [LICENSE](LICENSE).
