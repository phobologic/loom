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

## 7. Session 0 — narrative voice

**Preconditions:** 2-player game (Alice + Bob) in "Setup" status. Session 0 wizard seeded. The first 5 content prompts have been completed or skipped so the narrative voice step is active.
**Actions:**
1. Alice navigates to the narrative voice prompt.
2. Alice (organizer) clicks "Suggest voices". Three AI-generated voice options appear.
3. Bob clicks "Use this voice" on one of the options.
4. The page reloads showing the selected voice in the "Current narrative voice" block.
5. Alice enters a custom voice in the text area and clicks "Set custom voice".
6. The page reloads showing Alice's custom voice.
7. Alice clicks "Mark narrative voice complete".
**Pass criteria:**
- Voice suggestions appear as distinct prose-style descriptions (no raw JSON).
- Selecting a suggestion sets `game.narrative_voice` and shows it on the page.
- Writing and submitting a custom voice replaces any previously set voice.
- Marking complete advances the wizard to the next step.
- Non-organizer (Bob) can select a voice but cannot generate suggestions or mark complete.
**Severity if broken:** P1

---

## 7b. Session 0 — contribute + synthesize

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

## 18b. Act narrative on completion

**Preconditions:** Active act with at least one complete scene. `auto_generate_narrative` is enabled (default). Alice is a member.
**Actions:** Alice completes the act (single-player auto-approve or multi-player vote). Navigate to the scenes list page for that act (`/games/{id}/acts/{act_id}/scenes`).
**Pass criteria:** An "Act Narrative" section appears on the scenes page containing AI-generated prose. The narrative is read-only (no edit controls). If `auto_generate_narrative` is disabled on the game, the section does not appear.
**Severity if broken:** P1

---

## 19. Scene narrative on completion

**Preconditions:** Active scene with at least one canon beat. `auto_generate_narrative` is enabled (default). Alice is a member.
**Actions:** Alice completes the scene (single-player auto-approve or multi-player vote). Navigate to the scene detail page.
**Pass criteria:** A "Scene Narrative" section appears below the completion status, containing AI-generated prose. The narrative is read-only (no edit controls). If `auto_generate_narrative` is disabled on the game, the section does not appear.
**Severity if broken:** P1

---

## 19b. Tension adjustment on scene completion

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

---

## 28. NPC creation and editing (REQ-NPC-001)

**Preconditions:** Active game with Alice (organizer) and Bob (player) both logged in as members.
**Actions:**
1. Alice navigates to the game dashboard and clicks "NPCs" in the nav bar.
2. Alice fills in name "Thornwick", description "A weathered innkeeper", notes "Knows dark secrets", and submits.
3. Alice confirms Thornwick appears in the NPC list.
4. Bob logs in, navigates to the same game's NPC page.
5. Bob clicks "Edit" on Thornwick and changes the description to "A retired soldier turned innkeeper".
6. Bob saves changes.
**Pass criteria:**
- The "NPCs" nav link is visible on the dashboard for active games and absent for games in setup.
- Thornwick appears in the list after Alice creates it, with description and notes shown.
- Bob can see Thornwick on the NPC page (shared visibility).
- Bob's edit saves successfully and the updated description is shown immediately.
- No ownership error — any member can edit any NPC.
**Severity if broken:** P2

---

## 29. NPC creation from beat — manual (REQ-NPC-002)

**Preconditions:** Active game with Alice as a member. An active scene with at least one beat posted.
**Actions:**
1. Alice navigates to the scene detail page.
2. Locates a beat in the timeline and clicks "Add NPC from this beat".
3. On the NPC creation form, Alice fills in all three fields: "Who is this person?" → "The tavern keeper", Name → "Thornwick", "What do they want?" → "To keep his past buried".
4. Alice clicks "Create NPC" (without using the AI suggest button).
**Pass criteria:**
- The "Add NPC from this beat" link is visible on beats for active/paused games and absent for setup-status games.
- The NPC creation form shows the beat's narrative text in a context box.
- After submission, Alice is redirected to `/games/{id}/npcs`.
- Thornwick appears in the NPC list with the correct role/description and want/notes.
- All other game members receive an "NPC created" notification.
**Severity if broken:** P2

---

## 30. NPC creation from beat — AI assist (REQ-NPC-002)

**Preconditions:** Active game with Alice as a member. An active scene with at least one beat containing narrative text.
**Actions:**
1. Alice clicks "Add NPC from this beat" on a beat.
2. On the NPC creation form, Alice fills in only the "Who is this person?" field: "An imperial spy".
3. Alice clicks "Get AI ideas".
4. AI suggestions appear (name options and want options).
5. Alice clicks a name suggestion to populate the Name field.
6. Alice clicks a want suggestion to populate the "What do they want?" field.
7. Alice clicks "Create NPC".
**Pass criteria:**
- Clicking "Get AI ideas" sends an HTMX request and populates the suggestions area without a full page reload.
- Name suggestion pills appear; clicking one fills the Name input field.
- Want suggestion pills appear; clicking one fills the "What do they want?" input field.
- The player can edit the populated fields before submitting.
- After submission, the NPC appears on the `/games/{id}/npcs` page with the selected name and want.
- If AI is unavailable, the suggestions area shows a graceful "No suggestions available" message and does not block NPC creation.
**Severity if broken:** P2


---

## 31. World Entry CRUD (REQ-WORLD-001)

**Preconditions:** Active game with Alice as organizer and Bob as a player member.
**Actions:**
1. Alice navigates to the game dashboard and clicks "World Entries".
2. Alice fills in the creation form: Type → "Location", Name → "The Old Mill", Description → "A crumbling mill on the river.".
3. Alice clicks "Add Entry".
4. Bob (still logged in as Bob) navigates to `/games/{id}/world-entries`.
5. Bob clicks "Edit" on "The Old Mill" and adds more description, then saves.
**Pass criteria:**
- The "World Entries" nav link is visible on the game dashboard for active/paused games and absent during setup.
- After Alice creates the entry, she is redirected to the world entries list and "The Old Mill" appears with type "Location".
- Bob can see the entry without any ownership restriction.
- Bob can successfully edit the entry and his changes are saved.
- All other game members receive a "world entry created" notification when Alice creates the entry.
**Severity if broken:** P2

---

## 33. Relationship Tracking (REQ-WORLD-003)

**Preconditions:** Active game with Alice and Bob as members. At least two tracked entities exist (e.g., one NPC "Kira" and one NPC "Venn", or a character and a world entry).
**Actions:**
1. Alice navigates to `/games/{id}/relationships`.
2. Alice uses the "Add Relationship" form: selects Entity A (NPC: Kira), enters label "rivals with", selects Entity B (NPC: Venn), and submits.
3. Bob navigates to `/games/{id}/npcs`.
4. Bob navigates to `/games/{id}/relationships` and clicks "Delete" on the relationship.
**Pass criteria:**
- The `/relationships` page loads with a nav link visible from world-entries and NPC pages.
- After Alice creates the relationship, the page shows "Kira — rivals with — Venn".
- On the NPCs page, each NPC that has relationships shows them inline (e.g., "→ rivals with Venn").
- Bob receives a `relationship_created` notification when Alice adds the relationship.
- Deleting the relationship removes it from the list; no entries remain.
**Severity if broken:** P2

---

## 34. AI-Suggested Relationships (REQ-WORLD-003)

**Preconditions:** Active game with a `RelationshipSuggestion` row (status `pending`) seeded directly, with two valid NPCs as the entities.
**Actions:**
1. Alice navigates to `/games/{id}/relationships`.
2. The "AI-Suggested Relationships" section is visible with the pending suggestion.
3. Alice clicks "Accept" on the suggestion.
4. Bob seeds another suggestion and navigates to the page; Bob clicks "Dismiss".
**Pass criteria:**
- The suggestions banner appears only when pending suggestions exist; absent otherwise.
- Each suggestion shows the two entity names, the label, and the reason.
- Accepting creates a relationship row and marks the suggestion accepted; the suggestion disappears from the list.
- Dismissing removes the suggestion without creating a relationship.
- All members receive a `relationship_created` notification on accept.
**Severity if broken:** P2

---

## 32. AI-Suggested World Entries (REQ-WORLD-002)

**Preconditions:** Active game with Alice and Bob as members. A `WorldEntrySuggestion` row with status `pending` exists for the game (can be seeded directly in the DB for testing, as the trigger is a background AI task).
**Actions:**
1. Alice navigates to `/games/{id}/world-entries`.
2. The "AI Suggestions" section is visible with at least one pending suggestion.
3. Alice clicks "Accept" on the first suggestion.
4. Bob navigates to the world entries page and finds a second pending suggestion.
5. Bob clicks "Dismiss" on that suggestion.
**Pass criteria:**
- The "AI Suggestions" section appears above the entries list only when there are pending suggestions; it is absent otherwise.
- Each suggestion shows the name, type, description, and a brief reason.
- Clicking "Accept" creates a world entry matching the suggestion, removes it from the suggestions list, and sends a `world_entry_created` notification to other members.
- Clicking "Dismiss" removes the suggestion from view without creating an entry; no notification is sent.
- Both Accept and Dismiss redirect back to `/games/{id}/world-entries`.
**Severity if broken:** P2

---

## 35. Narrative export (REQ-PROSE-004)

**Preconditions:** A game with at least one complete act that has a narrative and at least one complete scene within that act that has a narrative.
**Actions:**
1. Navigate to `/games/{id}/acts/{act_id}/scenes/{scene_id}`. The "Scene Narrative" section is visible. Click "↓ Download scene narrative (.md)".
2. Verify the browser downloads a `.md` file. Confirm it contains the scene guiding question as a header and the narrative text.
3. Navigate to `/games/{id}/acts/{act_id}/scenes`. The "Act Narrative" section is visible. Click "↓ Download act narrative (.md)".
4. Verify the file contains the act guiding question, act narrative, and the scene narrative in order.
5. Navigate to `/games/{id}/acts`. Click "↓ Export all narratives (.md)".
6. Verify the file contains all completed acts and their scenes in order, with act/scene headers and guiding questions.
**Pass criteria:**
- All three download links appear only when the relevant narrative exists.
- The "Export all narratives" link does not appear on the acts page when no completed act has a narrative.
- Downloaded files open as valid markdown with `#`/`##`/`###` headers for game, act, and scene titles and guiding questions.
- Navigating directly to an export URL as a non-member returns a 403.
**Severity if broken:** P2
