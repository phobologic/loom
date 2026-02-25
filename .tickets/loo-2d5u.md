---
id: loo-2d5u
status: closed
deps: [loo-0pek]
links: []
created: 2026-02-25T01:22:41Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-rkvl
---
# Step 3: Dev Auth + User Scaffolding

A dev-only login page with a list of test users seeded on startup. Click a name, get a session, land on a 'my games' page. A clean 'get current user' dependency in FastAPI so real OAuth can swap in later. User model has display name and ID.

Real OAuth (REQ-AUTH-001) is deferred to Step 25.

## Acceptance Criteria

### REQ-AUTH-002: User Profile
*Requirement:* When a user has authenticated, Loom shall provide a user profile where they can set their display name and manage their account.
*Acceptance Criteria:*
- Users can set and update a display name.
- Users can see which games they belong to.
- Users can configure their notification preferences (see REQ-NOTIFY).

---

### REQ-AUTH-001: OAuth Authentication
*Requirement:* Loom shall support user authentication via OAuth providers, starting with Google and Discord.
*Acceptance Criteria:*
- Users can sign in using their Google account.
- Users can sign in using their Discord account.
- No email/password authentication is required for v1.
- A new user account is created automatically on first OAuth sign-in.
- Users have a display name (editable) and a unique internal ID.

NOTE: This requirement is DEFERRED to Step 25 (Real Auth). Step 3 implements dev-only auth as a placeholder.

