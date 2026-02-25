---
id: loo-lda5
status: closed
deps: []
links: [loo-cbf4]
created: 2026-02-25T02:29:08Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# update_game_settings blindly constructs enum values from raw form strings without error handling

**File**: loom/routers/games.py | **Line(s)**: 255-256 | **Description**: TieBreakingMethod(tie_breaking_method) and BeatSignificanceThreshold(beat_significance_threshold) will raise ValueError if the form submits an unrecognized string. No try/except surrounds these calls. An attacker submitting an invalid value gets an unhandled 500. | **Suggested Fix**: Wrap enum construction in try/except ValueError and raise HTTPException(status_code=422), or use a Pydantic form model for automatic validation.


## Notes

**2026-02-25T02:33:09Z**

Duplicate of loo-cbf4
