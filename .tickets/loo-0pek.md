---
id: loo-0pek
status: closed
deps: [loo-46aj]
links: []
created: 2026-02-25T01:22:41Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 2: Data Models + Migrations

Core SQLAlchemy models for the play loop, initial Alembic migration, database creates cleanly. No UI, but verifiable via tests or a script that can create a game, add an act, add a scene, add beats with events, etc.

**Models in this step:** User, Game, GameMember, Invitation, Act, Scene, Beat, Event, Character.

**Deferred to their feature steps:** WordSeedTable (Step 19), NPC/WorldEntry/Relationship (Phase 3).

## Acceptance Criteria

### REQ-TECH-003: Database Design
*Requirement:* Loom shall implement the data model as described in the Product Overview, using SQLAlchemy models.
*Acceptance Criteria:*
- All entities (Game, Act, Scene, Beat, Event, Character, NPC, WorldEntry, Relationship, WordSeedTable) are represented as SQLAlchemy models.
- Migrations are managed with Alembic.
- Foreign key relationships and cascading deletes are properly configured.
- All models include created_at and updated_at timestamps.
- The Beat model includes: author (FK to user), significance (major/minor), status (proposed/approved/canon/challenged/revised/rejected), and a relationship to multiple Events.
- The Event model includes: type (narrative/roll/oracle/fortune_roll/ooc), content, ordering within the beat, and type-specific fields (e.g., dice notation and result for roll events, oracle query and interpretations for oracle events, odds setting and tension level for fortune_roll events, word seed pair for oracle/fortune_roll events).
- The Scene model includes a tension integer field (1-9).
- The WordSeedTable model includes: a name, a genre/theme tag, a type (action or descriptor), and a list of words. Games have a many-to-many relationship with active WordSeedTables.

NOTE (Step 2 scope): Only the core play loop models are created in this step: User, Game, GameMember, Invitation, Act, Scene, Beat, Event, Character. WordSeedTable is deferred to Step 19. NPC, WorldEntry, Relationship are deferred to Phase 3.

