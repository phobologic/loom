---
id: loo-3x90
status: closed
deps: [loo-1u6r, loo-eolv]
links: []
created: 2026-02-26T20:27:54Z
type: task
priority: 2
assignee: Michael Barrett
---
# Auto-resolve open tension vote when a new scene is proposed

If a tension adjustment vote is still open when a player submits a new scene proposal, immediately resolve it using whatever votes have been cast (or the AI suggestion if zero votes), write the result to tension_carry_forward, and close the proposal. This prevents orphaned tension votes and ensures carry-forward is always set before the next scene begins.

UI requirement: the 'Propose a New Scene' form should detect an open tension vote and show a notice to the player, e.g. 'A tension adjustment vote is still open — proposing a new scene will resolve it automatically. If no votes have been cast, the AI suggestion will be applied.' The form should still submit normally; the notice is informational only (nudge, not a block).

Implementation touchpoints:
- scenes.py POST handler for scene proposal: check for open tension_adjustment proposal on the previous scene, resolve it before creating the new scene
- scenes.html: conditionally render the notice on the propose-scene form when an open tension vote exists for any complete scene in the act
- Pairs with loo-eolv (tension_carry_forward field and correct resolution logic must exist first)

