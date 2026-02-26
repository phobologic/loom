---
id: loo-wn7p
status: open
deps: [loo-1u6r]
links: []
created: 2026-02-26T20:55:56Z
type: feature
priority: 3
assignee: Michael Barrett
---
# Preserve tension adjustment AI rationale after vote resolves

Once the tension_adjustment vote resolves (all players voted, or timer expired), the proposal section disappears and the AI rationale is lost. Players have no way to revisit why tension moved from X to Y on a completed scene. Fix: after resolution, show a collapsed/static record on the completed scene detail page: 'Tension adjusted: 6 → 7. AI rationale: [text].' Similar pattern to how challenge history should be preserved (loo-pggr). The ai_rationale field already exists on VoteProposal — just need to surface it on the scene detail template when the proposal is approved and the scene is complete.

