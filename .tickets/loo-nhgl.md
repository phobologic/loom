---
id: loo-nhgl
status: closed
deps: [loo-1gkc]
links: []
created: 2026-02-25T01:22:44Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 22: In-App Notifications

Notification generation for all event types. Unread counts, mark as read.

## Acceptance Criteria

### REQ-NOTIFY-001: In-App Notifications
*Requirement:* Loom shall display in-app notifications for game activity requiring player attention.
*Acceptance Criteria:*
- Notifications are generated for: new beats in your game, votes requiring your input, oracle interpretations ready for review, challenges to your beats, spotlight/waiting-for-you indicators, AI suggestions (character updates, NPC entries, world entries, scene/act completion nudges), and auto-approval events.
- Unread notification count is visible on the game list and within each game.
- Notifications can be marked as read individually or in bulk.

