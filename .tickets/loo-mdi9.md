---
id: loo-mdi9
status: closed
deps: [loo-hdz8]
links: []
created: 2026-02-26T04:40:08Z
type: bug
priority: 1
assignee: Michael Barrett
---
# Oracle interpretation rendered as raw JSON/markdown

Parent: loo-hdz8 (Playwright smoke test findings epic). When an oracle event is invoked and the AI returns interpretations, the interpretation content in the beat timeline renders raw JSON/markdown formatting: first interpretation shows '```json', second shows '[', and text appears with trailing commas/quotes. The AI response is returning a JSON array as a code-fenced markdown block instead of plain text — parsing/rendering code is not stripping it. Reproduce: create 2-player game, complete session 0, enter scene play, invoke oracle — resulting beat timeline shows raw JSON instead of clean text. Screenshot: tests/e2e/screenshots/09-oracle-interpretations.png

