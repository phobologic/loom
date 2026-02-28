---
id: loo-1szi
status: closed
deps: [loo-u48z]
links: []
created: 2026-02-27T05:37:12Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-jy09
---
# Step 49: Narrative Export

Players can export narratives in markdown format. Options: individual scene narratives, individual act narratives, or a combined export of all completed act narratives in sequence. Export includes act and scene titles and guiding questions as structural headers.

## Requirements

### REQ-PROSE-004: Narrative Export
*Requirement:* Loom shall allow players to export narratives in markdown format.
*Acceptance Criteria:*
- Players can export individual scene narratives, individual act narratives, or a combined export of all completed act narratives in sequence.
- Export format is markdown.
- The export includes act and scene titles and guiding questions as structural headers.


## Notes

**2026-02-28T15:42:56Z**

Implemented three GET export endpoints returning text/plain markdown with Content-Disposition: attachment headers. Scene export at /games/{id}/acts/{act_id}/scenes/{scene_id}/export added to scenes.py; act and game exports at /games/{id}/acts/{act_id}/export and /games/{id}/export added to acts.py. Reused _load_game_for_acts and _load_scene_for_view for data loading. Game name is slugified (lowercase, hyphens, alphanumeric only, 50 char max) for the download filename. Added _act_label() and _game_slug() helpers. UI: export links added inside existing narrative sections in scene_detail.html and scenes.html; acts.html gets a conditional full-game export link gated on has_exportable_acts boolean passed from acts_view. Smoke manifest updated with workflow 35. 11 new tests in TestNarrativeExport, all passing alongside full suite (512 total).
