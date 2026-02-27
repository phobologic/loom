---
id: loo-1edk
status: open
deps: []
links: []
created: 2026-02-27T04:38:14Z
type: feature
priority: 4
assignee: Michael Barrett
parent: loo-1pwe
---
# Prompt versioning and A/B testing

Add a prompt versioning system so a new version of a prompt can run alongside the old one. When both versions are active, show the user both outputs and let them pick which is better. Track selections to determine statistically whether the new prompt outperforms the old before retiring it. Useful for iterating on prompts safely without guessing.


## Notes

**2026-02-27T04:43:51Z**

Approach: offline only, reconstruct from game state. Do NOT surface prompt comparisons to players during live play — keeps it out of the player experience and avoids conflict with 'AI assists, players decide' principle.

For the A/B mechanism: run both prompt versions against historical game data by reassembling context from existing DB records (beats, scenes, world doc, etc.) rather than storing raw prompts in AIUsageLog. AIUsageLog already captures feature, model, token counts, and context component names — enough to identify good candidate calls to replay, but not enough to replay them verbatim. That's fine; context reconstruction from game state is the right approach and avoids duplicating large text blobs in the logs.

What you'd need to build: a dev/admin tool that (1) queries AIUsageLog for historical calls of a given feature, (2) reassembles the context from the referenced game_id and surrounding DB state, (3) runs both prompt versions, (4) stores both outputs for human review. No player-facing UI needed.
