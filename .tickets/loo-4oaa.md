---
id: loo-4oaa
status: closed
deps: [loo-1u6r]
links: []
created: 2026-02-26T19:43:06Z
type: bug
priority: 1
assignee: Michael Barrett
tags: [playwright]
---
# Characters page shows Edit link to all players, not just the character owner

On /games/{id}/characters, the Edit link for each character should only be visible to the player who owns that character. During smoke test workflow 8, Alice could see the Edit link on Brother Cain (Bob's character) at /games/2/characters/4/edit. The snapshot showed both characters with Edit links from Alice's perspective. Bob correctly saw only an Edit link on his own character (Brother Cain). Fix: the server-rendered template should conditionally render the Edit link only when the current session user matches the character's owner.

