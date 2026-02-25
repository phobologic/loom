---
id: loo-zxdx
status: closed
deps: []
links: []
created: 2026-02-25T02:29:35Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# TimestampMixin updated_at relies on server_default instead of application-level default for SQLite

**File**: loom/models.py | **Line(s)**: 118-123 | **Description**: updated_at uses onupdate=func.now(). In SQLAlchemy with SQLite and aiosqlite, onupdate is an application-side mechanism — it fires when SQLAlchemy emits an UPDATE. However, direct DB-level updates (e.g. bulk updates via db.execute(update(...))) will not trigger it, leaving updated_at stale. This is a subtle correctness issue that is easy to hit as the codebase grows. server_default=func.now() similarly only fires on INSERT at the DB level for SQLite which does not support DEFAULT expressions being re-evaluated on UPDATE. | **Suggested Fix**: Use a Python-side default: default=datetime.utcnow and onupdate=datetime.utcnow (callable form), or accept the limitation and document it.


## Notes

**2026-02-25T02:39:35Z**

Closing: theoretical concern with no practical impact. The codebase contains no bulk/direct SQL UPDATE statements — all mutations go through SQLAlchemy model instances, which do trigger onupdate. Revisit if raw SQL updates are ever introduced.
