---
id: loo-jat3
status: closed
deps: []
links: []
created: 2026-02-25T04:51:36Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# migration 4763999af882 missing is_safety_tools column that model requires

**File**: alembic/versions/4763999af882_add_session0_tables.py, alembic/versions/b2458367ae3d_add_safety_tools.py
**Line(s)**: 4763999af882 upgrade(), b2458367ae3d upgrade()
**Description**: The Session0Prompt model (models.py) has an is_safety_tools column. The first migration (4763999af882) that creates the session0_prompts table does NOT include this column. It is added by the second migration (b2458367ae3d) via op.add_column. This means that any deployment that applies only 4763999af882 and then runs the application will encounter a missing column error when seeding defaults (_seed_defaults calls is_safety_tools=...). The column should have been included in the table creation migration, not added separately. While the two-migration approach works if both are applied together, it creates fragility in partial deployment scenarios and is architecturally wrong: the column belongs to the table definition.
**Suggested Fix**: Include is_safety_tools in the original create_table call in 4763999af882, and remove the op.add_column from b2458367ae3d (which can still add game_safety_tools). If the migrations are already applied to a production DB, add a compensating migration.

