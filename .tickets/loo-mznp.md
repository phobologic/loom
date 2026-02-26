---
id: loo-mznp
status: closed
deps: [loo-r4e4]
links: []
created: 2026-02-26T05:20:13Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-leil
---
# Step 35: Prose Expansion

After beat submission with narrative events, AI generates polished prose version in background using game's narrative voice and character voice notes. Shown only to author inline beneath original. Author can use, edit, or dismiss. Does not block submission. Both original and selected prose stored. Per-account preference (always/never/under N words). Requirements: REQ-PROSE-001.


## Notes

**2026-02-26T05:28:23Z**

Additional requirement details from REQ-PROSE-001 (needed for complete implementation):

**Edited indicator:** When the author applies a prose version, other players see the updated beat text with a subtle 'edited' indicator. The original text is replaced in the timeline but the change is visible.

**In-place voting update:** If the beat is a major beat currently in the voting flow when the author applies prose, the content updates in place without restarting the vote. The vote continues with the updated prose.

**Per-game preference override:** The per-account prose suggestion preference (always/never/under N words) can be overridden on a per-game basis. So a player could have a global default of 'always' but turn it off for a specific game, or vice versa.

**Storage requirement:** Both the original submitted text and the selected prose version (if any) must be stored — not just the final displayed version.
