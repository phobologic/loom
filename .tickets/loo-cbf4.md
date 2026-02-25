---
id: loo-cbf4
status: open
deps: []
links: [loo-lda5]
created: 2026-02-25T02:29:33Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:security]
---
# Unvalidated enum inputs in update_game_settings can raise unhandled ValueError

**File**: loom/routers/games.py | **Line(s)**: 255-256 | **Description**: TieBreakingMethod(tie_breaking_method) and BeatSignificanceThreshold(beat_significance_threshold) are called directly on raw form strings without try/except. A malformed POST with an unrecognised string will raise a ValueError that propagates as an unhandled 500 Internal Server Error, leaking a stack trace in debug mode. Although organizer-only, this is still a denial-of-service vector against the settings endpoint. | **Suggested Fix**: Wrap the enum coercions in try/except ValueError and raise HTTPException(status_code=422) with a descriptive message, or use Pydantic/FastAPI form models to validate enum fields before the handler body executes.

