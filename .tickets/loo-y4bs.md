---
id: loo-y4bs
status: open
deps: [loo-u2nv]
links: []
created: 2026-02-25T01:22:44Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 24: Word Seed Table Management

UI for selecting active tables during Session 0, adding custom words, viewing active tables.

## Acceptance Criteria

### REQ-ORACLE-006: Word Seed Tables
*Requirement:* Loom shall maintain word tables for use with the word seed oracle, organized by category.
*Acceptance Criteria:*
- Loom ships with a default set of action words and descriptor words.
- Tables are organized by genre or theme (general, fantasy, sci-fi, horror, noir, etc.).
- During Session 0, the group selects which table sets are active for their game. Multiple sets can be active simultaneously.
- Custom words can be added to a game's active tables by any player.
- Loom uses the active tables when generating word pairs, drawing one word from the action table and one from the descriptor table at random.

