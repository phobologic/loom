# Loom Development Plan

## Approach

The interface is the hardest part of this system and the biggest risk. The data model is a clean hierarchy and relatively straightforward. The business logic (state machines, voting, probability math) is well-specified in the requirements. But how async collaborative play *feels* to use will determine whether Loom works or not.

This plan front-loads user-facing flows so there's always something in the browser to iterate on. AI is stubbed until late in the process so interaction patterns can be refined without burning tokens. Auth is deferred in favor of a dev auth system that makes it easy to switch between test users for multi-player flow testing.

Each step builds on the previous ones and references the specific requirements it addresses.

### AI Stub Contract

Steps 1–22 stub all AI calls. Stubs must return **realistic hardcoded responses** — not empty strings or None. This keeps the UX testable throughout development. Examples:
- Significance classifier stub: always returns "minor"
- Oracle stub: returns 3 hardcoded interpretations with plausible text
- Session 0 synthesis stub: returns a paragraph of genre-appropriate placeholder prose
- World document stub: returns a short structured fake world document

When real AI is wired in (Step 23), the stubs are replaced with live calls through the same interface.

### Real-Time Updates

This is an async game where multiple players post beats independently. The UI must refresh without manual reloads. Use **HTMX polling** (`hx-trigger="every 5s"`) on the beat timeline and any other live-updating views. This is cheap to implement and sufficient for async play. SSE can replace polling later if needed. The polling strategy is introduced in Step 1's scaffolding notes and wired up in Step 12 (beat timeline).

---

## Phase 1: Core Loop

### Step 1: Project Scaffolding

Set up the repo, Python project with uv, FastAPI, Jinja2 templating, HTMX, PostgreSQL via docker-compose, SQLAlchemy + Alembic, config management for local/dev/prod environments, basic linting. A "hello world" page renders in the browser.

Note the AI stub contract and HTMX polling strategy (see Approach above) — these conventions apply from this step forward.

**Requirements:** REQ-TECH-001, REQ-TECH-004

---

### Step 2: Data Models + Migrations

Core SQLAlchemy models for the play loop, initial Alembic migration, database creates cleanly. No UI, but verifiable via tests or a script that can create a game, add an act, add a scene, add beats with events, etc.

**Models in this step:** User, Game, GameMember, Invitation, Act, Scene, Beat, Event, Character.

Deferred to their feature steps: WordSeedTable (Step 19), NPC/WorldEntry/Relationship (Phase 3).

**Requirements:** REQ-TECH-003

---

### Step 3: Dev Auth + User Scaffolding

A dev-only login page with a list of test users seeded on startup. Click a name, get a session, land on a "my games" page. A clean "get current user" dependency in FastAPI so real OAuth can swap in later. User model has display name and ID.

**Requirements:** REQ-AUTH-002 (partial), REQ-AUTH-001 (deferred)

---

### Step 4: Game Creation + Joining + Dashboard Shell

Create a game (name + optional pitch), get an invite link, join via invite link, see a game lobby showing current members. Organizer role assigned on creation. Player cap enforced.

Also establishes the **skeleton game dashboard** at this step: a persistent frame showing game name, current state, member list, and placeholder nav links (acts, settings, world doc). All subsequent steps wire into this shell rather than building standalone pages. The dashboard will fill in as later steps add content.

**Requirements:** REQ-GAME-001, REQ-GAME-002, REQ-GAME-003 (role assignment only)

---

### Step 5: Game Settings

The organizer can view and edit game settings. All configurable values with their defaults. Other players can view but not edit.

**Requirements:** REQ-GAME-004

---

### Step 6: Session 0 - The Wizard Flow

The structured prompt sequence: genre, tone, setting, central tension, themes. Players contribute text to each prompt, see each other's contributions. AI synthesis is stubbed (returns realistic placeholder prose per the stub contract). Players can navigate forward/back through prompts.

**Requirements:** REQ-S0-001, REQ-S0-002 (stubbed AI)

---

### Step 7: Safety Tools

Lines and veils interface within Session 0. Any player can add them. Stored with the game and visible to all members. Can also be added later during play.

**Requirements:** REQ-S0-006

---

### Step 8: Session 0 Completion + World Document

"Ready to play" proposal, early exit flow, world document generation (stubbed AI), group reviews and approves, game transitions from "setup" to "active." Includes a minimal voting mechanism to support the approval (yes/no votes, threshold check). Full voting comes in Step 17.

**Requirements:** REQ-S0-003, REQ-S0-005, REQ-GAME-005, REQ-VOTE-001 (minimal)

---

### Step 9: Character Creation

Each player creates a character (name, description, optional notes). Visible to all players. Editable by owner.

**Requirements:** REQ-CHAR-001

---

### Step 10: Game Dashboard - Full Content

The game dashboard shell (introduced in Step 4) is now populated with real content: game state, members, link to world document, list of acts, active act and its scenes. The player's home base for the game.

**Requirements:** No single requirement - ties together REQ-GAME-005, act/scene structure, and navigation.

---

### Step 11: Act Creation

Any player proposes a new act with a guiding question. Goes through voting/approval. On approval, the act becomes active.

**Requirements:** REQ-ACT-001, REQ-VOTE-001, REQ-VOTE-002

---

### Step 12: Scene Creation + Character Presence

Propose a scene with guiding question, initial characters present, optional location. Goes through voting. Characters present list is displayed and updatable.

**Requirements:** REQ-SCENE-001, REQ-SCENE-004

---

### Step 13: Scene View + Beat Timeline

The main play view. Scene info (guiding question, characters present, tension), beat timeline in chronological order, beat submission area (placeholder). Start with displaying beats only.

Wire up **HTMX polling** on the timeline here (`hx-trigger="every 5s"`) so new beats from other players appear without a page reload.

**Requirements:** REQ-BEAT-006, REQ-TENSION-001 (display only)

---

### Step 14: Beat Submission - Narrative Only

Compose and submit a beat with a single narrative event. Appears in the timeline. All beats treated as minor (instant canon) for now.

**Requirements:** REQ-BEAT-001, REQ-BEAT-002 (narrative type only), REQ-BEAT-003 (minor path only)

---

### Step 15: Beat Submission - Multi-Event

Extend the beat composer to support multiple events of different types in a single beat. Narrative, OOC, and rolls (without dice rolling yet). Primarily a UI/interaction design step.

**Requirements:** REQ-BEAT-001, REQ-BEAT-002

---

### Step 16: Dice Rolling

Dice rolling within roll events. Standard notation parsing, server-side execution, result display in the timeline.

**Requirements:** REQ-DICE-001, REQ-DICE-002

---

### Step 17: Beat Significance Classification

AI suggests major/minor (stubbed), player accepts or overrides. Major beats enter the voting flow. Full beat lifecycle state machine is now active.

**Requirements:** REQ-BEAT-003 (full lifecycle), REQ-BEAT-004

---

### Step 18: Voting - Full Implementation + Silence Timer

Complete voting system. Threshold calculation, yes/no/suggest modification, vote display, tie-breaking configuration. Silence timer included: configurable duration, countdown display, auto-approval on expiry, player notification when auto-approval fires. Timer resets if a modification is suggested.

The minimal voting introduced in Step 8 is replaced/upgraded here.

**Requirements:** REQ-VOTE-001, REQ-VOTE-002, REQ-GAME-004 (timer config)

---

### Step 19: Oracle - Invocation + Word Seeds

Player invokes the oracle with a question. Word seed pair generated from active tables (seeded default data). AI generates interpretations (stubbed — returns 3 hardcoded plausible interpretations). Results displayed to all players. Player can **re-roll or lock the word pair** before triggering generation (per REQ-ORACLE-005). The word pair is stored alongside the result.

WordSeedTable model and default seed data (general + genre sets) added in this step.

**Requirements:** REQ-ORACLE-001, REQ-ORACLE-002 (stubbed), REQ-ORACLE-005, REQ-ORACLE-006

---

### Step 20: Oracle - Discussion + Selection

Vote on interpretations, comment, propose alternatives. Invoker makes final selection. Selected interpretation can be woven into a beat.

**Requirements:** REQ-ORACLE-003, REQ-ORACLE-004

---

### Step 21: Fortune Roll

Yes/no oracle. Player sets odds, tension modifies probability, roll executes, result displayed. Exceptional results flagged as major beats. Odds contestation window.

**Requirements:** REQ-ORACLE-007, REQ-TENSION-001, REQ-TENSION-003

---

### Step 22: In-App Notifications

Notification generation for all event types. Unread counts, mark as read.

**Requirements:** REQ-NOTIFY-001

---

### Step 23: AI Integration - Real Calls

Replace all stubbed AI with real Anthropic API calls through the abstraction layer. Context assembly, per-feature model configuration. Covers oracle, Session 0 synthesis, world document generation, significance classification.

**Requirements:** REQ-AI-001, REQ-AI-003, REQ-AI-004

---

### Step 24: Word Seed Table Management

UI for selecting active tables during Session 0, adding custom words, viewing active tables.

**Requirements:** REQ-ORACLE-006

---

### Step 25: Real Auth

OAuth with Google and Discord, user creation on first sign-in, session management. Replace the dev auth dependency with the real implementation.

**Requirements:** REQ-AUTH-001, REQ-AUTH-002 (complete)
