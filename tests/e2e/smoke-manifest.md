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

---

## 16. Scene completion

**Preconditions:** Active scene (from workflow 10). Alice is a member.
**Actions:** Alice navigates to the scene detail page. Clicks "Propose Scene Completion". In a single-player game, auto-approves immediately. In a multi-player game, second player navigates to scene and votes yes.
**Pass criteria:** Scene status shows "Complete". Beat submission form is no longer visible. Scene appears as a link on the scenes list page.
**Severity if broken:** P1

---

## 17. Act completion

**Preconditions:** Active act with at least one complete scene (from workflow 16). Alice is a member.
**Actions:** Alice navigates to the scenes list for the act (`/games/{id}/acts/{act_id}/scenes`). Clicks "Propose Act Completion". In a single-player game, auto-approves. In a multi-player game, second player votes yes.
**Pass criteria:** Act status shows "Complete" on acts page. Scenes page for the completed act remains accessible (HTTP 200). "Propose a New Scene" form is no longer visible.
**Severity if broken:** P1

---

## 18. Tension adjustment on scene completion

**Preconditions:** Scene has just been completed (workflow 16 done). In a multi-player game, all members present.
**Actions:** After scene completion vote passes, navigate to the scene detail page. Observe the "Tension Adjustment" section with the AI's recommendation (+1/-1/0) and rationale explaining scene-level and arc-level reasoning. In a single-player game, tension adjusts automatically (no voting section). In a multi-player game, each player votes +1 (Escalate), 0 (Hold steady), or -1 (Ease tension). After all players have voted, reload the page.
**Pass criteria:** After all votes — the tension adjustment section disappears (proposal resolved). The scene's tension value reflects the plurality delta (clamped 1-9). The adjusted tension appears as the default on the next scene proposal form. If the expiry window passes with no votes, the AI suggestion is applied automatically. Single-player: tension auto-adjusts immediately after scene completion, no vote UI shown.
**Severity if broken:** P2

---

## 19. Challenge beat — author accepts and revises

**Preconditions:** Active scene with a canon minor beat. Two members: Alice (beat author, user 1), Bob (user 2).
**Actions:** Bob challenges Alice's beat with a reason. Alice navigates to the scene detail page. The beat shows `[Challenged]` with Bob's reason. Alice expands "Accept & revise", types revised content, and submits. In a 2-player game, Bob votes yes on the revised beat.
**Pass criteria:** After Alice accepts, beat shows `[Pending vote]`. After Bob votes yes, beat returns to `[Canon]` with the revised content visible. The original challenge reason is no longer displayed.
**Severity if broken:** P1

---

## 20. Challenge beat — author dismisses, group can comment

**Preconditions:** Active scene with a canon minor beat. Two members: Alice (beat author, user 1), Bob (user 2).
**Actions:** Bob challenges Alice's beat. Bob (or Alice) adds a comment via the comment form below the challenge. Alice navigates to the scene detail page, reads the comment, and clicks "Dismiss — beat stands as written."
**Pass criteria:** Beat returns to `[Canon]` status. Challenge reason is no longer displayed. Bob receives a notification that the challenge was dismissed. The comment thread remains visible in the beat display.
**Severity if broken:** P1
