---
id: loo-9gfl
status: open
deps: [loo-y4bs]
links: []
created: 2026-02-25T01:22:44Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 25: Real Auth

OAuth with Google and Discord, user creation on first sign-in, session management. Replace the dev auth dependency with the real implementation.

## Acceptance Criteria

### REQ-AUTH-001: OAuth Authentication
*Requirement:* Loom shall support user authentication via OAuth providers, starting with Google and Discord.
*Acceptance Criteria:*
- Users can sign in using their Google account.
- Users can sign in using their Discord account.
- No email/password authentication is required for v1.
- A new user account is created automatically on first OAuth sign-in.
- Users have a display name (editable) and a unique internal ID.

NOTE: This requirement is DEFERRED to Step 25 (Real Auth). Step 3 implements dev-only auth as a placeholder.

---

### REQ-AUTH-002: User Profile
*Requirement:* When a user has authenticated, Loom shall provide a user profile where they can set their display name and manage their account.
*Acceptance Criteria:*
- Users can set and update a display name.
- Users can see which games they belong to.
- Users can configure their notification preferences (see REQ-NOTIFY).

