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

## 6. Remove player

**Preconditions:** Game exists with Alice as organizer and Bob as a player member.
**Actions:** Alice navigates to the game detail page. Clicks the "Remove" link next to Bob. Sees the confirmation page showing Bob's name and a three-word passphrase. Types the passphrase into the input field. Submits.
**Pass criteria:** Redirect back to the game detail page. Bob no longer appears in the member list. If Alice types the wrong passphrase, the page re-renders with "Incorrect code — try again" and Bob remains a member.
**Severity if broken:** P1

---

## 7. Session 0 — contribute + synthesize

**Preconditions:** 2-player game (Alice + Bob) in "Setup" status.
**Actions:** Alice and Bob each submit a response to prompt 1. Alice clicks "Synthesize contributions".
**Pass criteria:** AI synthesis text appears as readable prose — no raw JSON, no backticks, no array brackets. "Accept synthesis" button is present.
**Severity if broken:** P1
**Known issue:** loo-mdi9 (oracle JSON rendering) — may also affect synthesis output formatting.

---

## 8. Session 0 — complete → game active

**Preconditions:** 2-player game. At least one prompt synthesized and accepted; remaining prompts skipped.
**Actions:** Alice clicks "Generate World Document & Start Vote". Both players vote Yes.
**Pass criteria:** World document page shows "Status: Approved". Game dashboard shows "Status: Active".
**Severity if broken:** P0

---

## 9. Character creation

**Preconditions:** Active game with Alice and Bob as members.
**Actions:** Alice creates a character with name and description. Bob creates a character.
**Pass criteria:** `/games/{id}/characters` shows both characters with correct owners. Alice cannot see an "Edit" link on Bob's character.
**Severity if broken:** P1

---

## 10. Act proposal + voting

**Preconditions:** Active game with 2 players.
**Actions:** Alice navigates to `/games/{id}/acts`, fills and submits the propose act form. Bob votes Yes.
**Pass criteria:** After Bob's vote, act status = Active. Acts list shows the act with a link to its scenes.
**Severity if broken:** P1

---

## 11. Scene proposal + voting

**Preconditions:** Active act. Both characters exist.
**Actions:** Alice proposes a scene (guiding question, location, tension, both characters selected). Bob votes Yes.
**Pass criteria:** Scene status = Active. Scenes list shows link to scene detail.
**Severity if broken:** P1

---

## 12. Narrative beat

**Preconditions:** Active scene.
**Actions:** Alice submits a narrative beat (text only, minor significance).
**Pass criteria:** Beat appears in the timeline immediately (minor = instant canon, no vote needed). Timeline shows the text content.
**Severity if broken:** P0 — this is the core play loop.

---

## 13. Dice roll beat

**Preconditions:** Active scene.
**Actions:** Alice clicks "+ Roll" to add a roll event, enters `2d6` notation and a reason, submits beat.
**Pass criteria:** Beat appears in timeline showing the roll notation, a numeric result, and the reason text.
**Severity if broken:** P1

---

## 14. Oracle invocation + selection

**Preconditions:** Active scene.
**Actions:** Alice clicks "+ Oracle". A word pair is shown. Alice enters a question and submits. Alice clicks "Select #1".
**Pass criteria:** 3 interpretations appear as readable prose (no raw JSON/backticks). After selection, oracle shows "Selected" status with no further vote buttons.
**Severity if broken:** P1
**Known issue:** loo-mdi9 — interpretation text may render as raw JSON.

---

## 15. Fortune roll

**Preconditions:** Active scene.
**Actions:** Bob navigates to fortune roll via "+ Fortune Roll" link. Enters a yes/no question, selects "Likely" odds, submits.
**Pass criteria:** Beat appears in timeline showing "fortune roll", the question, odds, tension, and "Pending — resolves after contest window" status.
**Severity if broken:** P2

---

## 16. Notifications

**Preconditions:** Alice has submitted at least one beat in an active game that Bob is a member of.
**Actions:** Bob navigates to `/notifications`.
**Pass criteria:** At least one "A new beat was submitted" notification is visible.
**Severity if broken:** P2

---

## 17. Scene completion

**Preconditions:** Active scene (from workflow 10). Alice is a member.
**Actions:** Alice navigates to the scene detail page. Clicks "Propose Scene Completion". In a single-player game, auto-approves immediately. In a multi-player game, second player navigates to scene and votes yes.
**Pass criteria:** Scene status shows "Complete". Beat submission form is no longer visible. Scene appears as a link on the scenes list page.
**Severity if broken:** P1

---

## 18. Act completion

**Preconditions:** Active act with at least one complete scene (from workflow 16). Alice is a member.
**Actions:** Alice navigates to the scenes list for the act (`/games/{id}/acts/{act_id}/scenes`). Clicks "Propose Act Completion". In a single-player game, auto-approves. In a multi-player game, second player votes yes.
**Pass criteria:** Act status shows "Complete" on acts page. Scenes page for the completed act remains accessible (HTTP 200). "Propose a New Scene" form is no longer visible.
**Severity if broken:** P1

---

## 19. Tension adjustment on scene completion

**Preconditions:** Scene has just been completed (workflow 16 done). In a multi-player game, all members present.
**Actions:** After scene completion vote passes, navigate to the scene detail page. Observe the "Tension Adjustment" section with the AI's recommendation (+1/-1/0) and rationale explaining scene-level and arc-level reasoning. In a single-player game, tension adjusts automatically (no voting section). In a multi-player game, each player votes +1 (Escalate), 0 (Hold steady), or -1 (Ease tension). After all players have voted, reload the page.
**Pass criteria:** After all votes — the tension adjustment section disappears (proposal resolved). The scene's tension value reflects the plurality delta (clamped 1-9). The adjusted tension appears as the default on the next scene proposal form. If the expiry window passes with no votes, the AI suggestion is applied automatically. Single-player: tension auto-adjusts immediately after scene completion, no vote UI shown.
**Severity if broken:** P2

---

## 20. Challenge beat — author accepts and revises

**Preconditions:** Active scene with a canon minor beat. Two members: Alice (beat author, user 1), Bob (user 2).
**Actions:** Bob challenges Alice's beat with a reason. Alice navigates to the scene detail page. The beat shows `[Challenged]` with Bob's reason. Alice expands "Accept & revise", types revised content, and submits. In a 2-player game, Bob votes yes on the revised beat.
**Pass criteria:** After Alice accepts, beat shows `[Pending vote]`. After Bob votes yes, beat returns to `[Canon]` with the revised content visible. The original challenge reason is no longer displayed.
**Severity if broken:** P1

---

## 21. Challenge beat — author dismisses, group can comment

**Preconditions:** Active scene with a canon minor beat. Two members: Alice (beat author, user 1), Bob (user 2).
**Actions:** Bob challenges Alice's beat. Bob (or Alice) adds a comment via the comment form below the challenge. Alice navigates to the scene detail page, reads the comment, and clicks "Dismiss — beat stands as written."
**Pass criteria:** Beat returns to `[Canon]` status. Challenge reason is no longer displayed. Bob receives a notification that the challenge was dismissed. The comment thread remains visible in the beat display.
**Severity if broken:** P1

---

## 22. Consecutive beat nudge (REQ-PACE-001)

**Preconditions:** Active scene. Alice is a member. `max_consecutive_beats` setting is 3 (default). Alice has already submitted 2 consecutive IC beats with no beat by another player in between.
**Actions:** Alice submits a third IC beat.
**Pass criteria:** Scene page shows a yellow nudge banner: "You've posted the last 3 beats — maybe see if others want to jump in?" The beat is still submitted and appears in the timeline normally. The nudge does not prevent further posting.
**Severity if broken:** P2

---

## 23. Contribution visibility (REQ-PACE-002)

**Preconditions:** Active scene with at least one IC beat posted by any player.
**Actions:** Navigate to the scene detail page.
**Pass criteria:** A "Contributions this scene:" panel appears above the beat timeline, listing each game member by name with their IC beat count and a proportional bar. Members with zero beats show "0 beats" and no bar. The panel refreshes when new beats are posted (via HTMX polling every 5 seconds).
**Severity if broken:** P2

---

## 24. Spotlight / Waiting for Response (REQ-PACE-003)

**Preconditions:** Active scene with at least 2 characters present owned by different players (Alice owns Character A, Bob owns Character B).
**Actions:**
1. Alice submits a beat and selects "Character B" in the "Spotlight (optional)" dropdown.
2. Verify Bob receives a spotlight notification.
3. Navigate to the scene detail page.
**Pass criteria:**
- The "Characters present" list shows Character B with a ⏳ badge.
- An amber spotlight banner appears: "⏳ Character B is in the spotlight — someone is waiting for a response."
- Alice's beat in the timeline shows "⏳ Waiting for Character B."
- Bob submits any beat → spotlight resolves: banner disappears, Alice's beat now shows "[Response received from Character B]" (muted), Character B badge clears.
- After `silence_timer_hours` have elapsed from the spotlight beat, the banner and ⏳ indicators no longer appear (spotlight expired).
- If no characters other than Alice's are present in the scene, the "Spotlight" dropdown does not appear.
**Severity if broken:** P2

---

## 25. Prose expansion (REQ-PROSE-001)

**Preconditions:** Active scene. Alice's account has prose_mode set to "always" (the default). At least one character is present in the scene.
**Actions:**
1. Alice submits a beat with a narrative event.
2. Wait for the background task to run (a few seconds; the beat timeline polls automatically).
3. Alice observes the scene page.
**Pass criteria:**
- The beat is submitted immediately and appears in the timeline (minor → canon, major → voting) without delay.
- Within a few seconds, an amber "Prose suggestion" panel appears inline below Alice's narrative text, visible only to Alice.
- The panel shows the AI-generated prose text, an "Apply" button, an "Edit & Apply" disclosure, and a "Dismiss" button.
- Clicking "Apply" replaces the displayed beat text with the prose version. A small "edited" label appears. A collapsed "Show original" disclosure beneath it reveals the original submitted text.
- Other players (Bob) see the updated text with the "edited" label on their next poll; they do not see the suggestion panel.
- Clicking "Dismiss" removes the suggestion panel; the original text remains unchanged.
- Clicking "Edit & Apply" allows Alice to modify the prose before applying; the edited version is stored and displayed.
- If Alice's prose_mode is "never", no suggestion panel appears for any beat.
**Severity if broken:** P1

---

## 26. AI Pre-submission Consistency Check (REQ-BEAT-005)

**Preconditions:** Active scene with at least one existing canon beat and a world document. Alice is a member.
**Actions:**
1. Alice adds a narrative event to the beat composer with content that clearly contradicts the established fiction (e.g., a character takes an action they were established as unable to do).
2. Alice clicks "Submit Beat" (the normal submit button).
3. Wait for the consistency check to complete (button shows "Checking…").
**Pass criteria:**
- The submit button becomes "Checking…" while the AI check runs.
- If the AI finds no issues, the form submits normally (beat appears in the timeline).
- If the AI finds issues, an amber warning box appears below the form listing the flags as a bulleted list. Two new buttons appear: "Submit Anyway" and "Revise".
- "Submit Anyway" submits the beat without changes — it appears in the timeline.
- "Revise" dismisses the warning box and re-enables the "Submit Beat" button, allowing Alice to edit the beat.
- The check is advisory only — the beat is never blocked.
- If the AI is unavailable, the form submits normally (no error shown, no blocking).
- Other players (Bob) are not shown the consistency warning — it is visible only to the author before submission.
**Severity if broken:** P2

---

## 27. Fortune Roll — Oracle Follow-up Link (REQ-ORACLE-008)

**Preconditions:** Active scene. A fortune roll beat has been submitted by Alice and has resolved (contest window expired). Alice is logged in.
**Actions:**
1. Navigate to the scene detail page.
2. Locate the resolved fortune roll beat in the timeline.
3. Click "Ask the oracle about this →" link below the result.
**Pass criteria:**
- An "Ask the oracle about this →" link is visible below the resolved result badge, visible only to Alice (the invoker).
- Clicking the link navigates to the oracle form for that scene.
- The oracle question textarea is pre-filled with the original fortune roll question.
- Bob (non-invoker) viewing the same scene does not see the link.
**Severity if broken:** P2
