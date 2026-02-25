---
id: loo-j8vl
status: open
deps: [loo-i3rj]
links: []
created: 2026-02-25T01:22:43Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 19: Oracle - Invocation + Word Seeds

Player invokes the oracle with a question. Word seed pair generated from active tables (seeded default data). AI generates interpretations (stubbed — returns 3 hardcoded plausible interpretations). Results displayed to all players. Player can **re-roll or lock the word pair** before triggering generation (per REQ-ORACLE-005). The word pair is stored alongside the result.

WordSeedTable model and default seed data (general + genre sets) added in this step.

## Acceptance Criteria

### REQ-ORACLE-001: Oracle Query
*Requirement:* When a player wants AI-generated suggestions for what happens next, Loom shall provide an oracle that generates interpretations based on the game's context.
*Acceptance Criteria:*
- Any player can invoke the oracle at any time during an active scene.
- The player provides a question or context and optionally includes raw oracle/roll results to interpret.
- The oracle generates multiple interpretations (configurable count, default 3-5).
- Oracle queries can be embedded as an event within a beat.

---

### REQ-ORACLE-002: Oracle Context
*Requirement:* When the oracle is invoked, Loom shall provide the AI with rich context about the current game state.
*Acceptance Criteria:*
- Context includes: the world document, current act guiding question and summary, current scene guiding question and description, participating character descriptions, relevant NPC entries, relevant world entries, recent beat history, and lines and veils.
- Loom does not include all beats or all scenes - it provides overall context plus recent detail.
- Loom tracks token usage per oracle call for future optimization.

NOTE: AI is stubbed in this step. Stub returns 3 hardcoded plausible interpretations.

---

### REQ-ORACLE-005: Word Seed Oracle
*Requirement:* When the interpretive oracle is invoked, Loom shall generate a random word pair to serve as a creative seed for the AI's interpretations.
*Acceptance Criteria:*
- Loom generates a pair of random words: one action/verb (e.g., "abandon," "betray," "protect") and one descriptor/subject (e.g., "mechanical," "dreams," "authority").
- The word pair is displayed to the player and the group before and alongside the oracle's interpretations.
- The AI is instructed to weave the word pair's themes into its interpretations as lateral inspiration.
- The word pair is drawn from system-maintained word tables (not from any copyrighted source).
- The word tables should be extensible - Loom ships with a default general-purpose set, and genre-specific sets can be selected during Session 0.
- Players can **lock or re-roll the word pair** before the oracle generates interpretations.
- The word pair and chosen interpretation are stored together for reference.

---

### REQ-ORACLE-006: Word Seed Tables
*Requirement:* Loom shall maintain word tables for use with the word seed oracle, organized by category.
*Acceptance Criteria:*
- Loom ships with a default set of action words and descriptor words.
- Tables are organized by genre or theme (general, fantasy, sci-fi, horror, noir, etc.).
- During Session 0, the group selects which table sets are active for their game. Multiple sets can be active simultaneously.
- Custom words can be added to a game's active tables by any player.
- Loom uses the active tables when generating word pairs, drawing one word from the action table and one from the descriptor table at random.

