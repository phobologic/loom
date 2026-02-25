---
id: loo-6vjh
status: open
deps: []
links: []
created: 2026-02-25T02:29:43Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:perf]
---
# Event.interpretations property deserializes JSON on every property access

**File**: loom/models.py
**Line(s)**: 357-367
**Description**: The interpretations property calls json.loads on every read access. If a template or business logic accesses this property multiple times within one request (e.g., iterating events and checking interpretations twice), the JSON string is deserialized each time with no caching.

**Suggested Fix**: Use SQLAlchemy's built-in JSON column type instead of manual serialization, which integrates naturally with the ORM and avoids the property pattern entirely:

    oracle_interpretations: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

Alternatively, cache the deserialized result in a private attribute on first access:

    @property
    def interpretations(self) -> list[str]:
        if self.oracle_interpretations is None:
            return []
        if not hasattr(self, '_interp_cache'):
            object.__setattr__(self, '_interp_cache', json.loads(self.oracle_interpretations))
        return self._interp_cache

The JSON column approach is cleaner and leverages the ORM's type system.

