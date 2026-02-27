---
id: loo-9gyk
status: open
deps: [loo-6hc9]
links: []
created: 2026-02-27T05:38:38Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-jy09
---
# Step 51: AI Nudge for Act Completion

Same pattern as scene completion nudges but for acts. The AI monitors for signals that the act's guiding question has been answered and suggests the group consider completing the act. Non-blocking; players can dismiss or initiate the completion proposal. The AI does not auto-complete acts.

## Requirements

### REQ-ACT-003: AI Nudge for Act Completion
*Requirement:* When the AI detects that an act's guiding question may have been answered, it shall suggest that the group consider completing the act.
*Acceptance Criteria:*
- The AI monitors the fiction for signals that the guiding question has been resolved.
- The suggestion is surfaced to all players as a non-blocking prompt.
- Players can dismiss the suggestion or initiate the completion proposal.
- The AI does not auto-complete acts.

