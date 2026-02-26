# Smoke Test Manifest

Ordered list of workflows tested by `/smoketest`. Each entry defines: preconditions, what to exercise, pass criteria, and default failure severity.

**Maintaining this file:** Add a new entry whenever a new user-facing workflow is implemented. Place it in logical test order (dependencies first). See `CLAUDE.md` for the rule.

---

## 1. Auth — dev login

**Preconditions:** None
**Actions:** Navigate to `/dev/login`. Click the "Alice" button.
**Pass criteria:** Redirect to `/games`. Page shows "Logged in as: Alice".
**Severity if broken:** P0 — all other workflows depend on this.

---

## 2. Auth — unauthenticated redirect

**Preconditions:** No active session (use a fresh browser context).
**Actions:** Navigate to `/games` without logging in.
**Pass criteria:** Redirect to `/login`.
**Severity if broken:** P1

---

## 3. Game creation

**Preconditions:** Logged in as Alice.
**Actions:** On `/games`, fill game name and optional pitch, submit.
**Pass criteria:** Redirect to `/games/{id}`. Dashboard shows the correct game name, status "Setup", and an invite link.
**Severity if broken:** P0

---

## 4. Invite + join

**Preconditions:** Game exists with Alice as organizer (from workflow 3). Bob is logged in via a separate browser session.
**Actions:** Bob navigates to the invite URL. Clicks "Join game".
**Pass criteria:** Redirect to `/games/{id}`. Member list shows "Members (2/5)" with Alice (organizer) and Bob.
**Severity if broken:** P1

---

## 5. Game settings

**Preconditions:** Game exists. Logged in as Alice (organizer).
**Actions:** Navigate to `/games/{id}/settings`. Change the silence timer value. Save.
**Pass criteria:** Page reloads with the updated value shown.
**Severity if broken:** P2

---

## 6. Session 0 — contribute + synthesize

**Preconditions:** 2-player game (Alice + Bob) in "Setup" status.
**Actions:** Alice and Bob each submit a response to prompt 1. Alice clicks "Synthesize contributions".
**Pass criteria:** AI synthesis text appears as readable prose — no raw JSON, no backticks, no array brackets. "Accept synthesis" button is present.
**Severity if broken:** P1
**Known issue:** loo-mdi9 (oracle JSON rendering) — may also affect synthesis output formatting.

---

## 7. Session 0 — complete → game active

**Preconditions:** 2-player game. At least one prompt synthesized and accepted; remaining prompts skipped.
**Actions:** Alice clicks "Generate World Document & Start Vote". Both players vote Yes.
**Pass criteria:** World document page shows "Status: Approved". Game dashboard shows "Status: Active".
**Severity if broken:** P0

---

## 8. Character creation

**Preconditions:** Active game with Alice and Bob as members.
**Actions:** Alice creates a character with name and description. Bob creates a character.
**Pass criteria:** `/games/{id}/characters` shows both characters with correct owners. Alice cannot see an "Edit" link on Bob's character.
**Severity if broken:** P1

---

## 9. Act proposal + voting

**Preconditions:** Active game with 2 players.
**Actions:** Alice navigates to `/games/{id}/acts`, fills and submits the propose act form. Bob votes Yes.
**Pass criteria:** After Bob's vote, act status = Active. Acts list shows the act with a link to its scenes.
**Severity if broken:** P1

---

## 10. Scene proposal + voting

**Preconditions:** Active act. Both characters exist.
**Actions:** Alice proposes a scene (guiding question, location, tension, both characters selected). Bob votes Yes.
**Pass criteria:** Scene status = Active. Scenes list shows link to scene detail.
**Severity if broken:** P1

---

## 11. Narrative beat

**Preconditions:** Active scene.
**Actions:** Alice submits a narrative beat (text only, minor significance).
**Pass criteria:** Beat appears in the timeline immediately (minor = instant canon, no vote needed). Timeline shows the text content.
**Severity if broken:** P0 — this is the core play loop.

---

## 12. Dice roll beat

**Preconditions:** Active scene.
**Actions:** Alice clicks "+ Roll" to add a roll event, enters `2d6` notation and a reason, submits beat.
**Pass criteria:** Beat appears in timeline showing the roll notation, a numeric result, and the reason text.
**Severity if broken:** P1

---

## 13. Oracle invocation + selection

**Preconditions:** Active scene.
**Actions:** Alice clicks "+ Oracle". A word pair is shown. Alice enters a question and submits. Alice clicks "Select #1".
**Pass criteria:** 3 interpretations appear as readable prose (no raw JSON/backticks). After selection, oracle shows "Selected" status with no further vote buttons.
**Severity if broken:** P1
**Known issue:** loo-mdi9 — interpretation text may render as raw JSON.

---

## 14. Fortune roll

**Preconditions:** Active scene.
**Actions:** Bob navigates to fortune roll via "+ Fortune Roll" link. Enters a yes/no question, selects "Likely" odds, submits.
**Pass criteria:** Beat appears in timeline showing "fortune roll", the question, odds, tension, and "Pending — resolves after contest window" status.
**Severity if broken:** P2

---

## 15. Notifications

**Preconditions:** Alice has submitted at least one beat in an active game that Bob is a member of.
**Actions:** Bob navigates to `/notifications`.
**Pass criteria:** At least one "A new beat was submitted" notification is visible.
**Severity if broken:** P2
