# Loom Development Plan - Phase 2: Polish and Safety

## Approach

Phase 2 builds on the core play loop established in Phase 1. The main additions are: completing scenes and acts (which Phase 1 left out), the challenge system for disputing canon, pacing controls, prose expansion, and several AI-powered features that improve the quality of play without changing the fundamental flow.

Scene and act completion are pulled forward from Phase 3 into early Phase 2 because multiple features here depend on them - tension adjustment triggers on scene completion, AI-suggested character updates trigger on scene completion, and the gameplay loop isn't really complete without a way to finish things and move on.

AI usage tracking comes in at Step 27, immediately after scene completion, so that all subsequent Phase 2 AI features are built on the logging infrastructure from the start.

Character voice notes are introduced before prose expansion because prose expansion uses them.

AI calls are real from Phase 1 Step 23 onward, so all AI features in Phase 2 use live calls through the abstraction layer.

---

### Step 26: Scene Completion + Act Completion

The basic mechanism: any player proposes completing the current scene or act, group votes, on approval it's marked complete and becomes read-only. No AI nudges yet (those are Phase 3), no narrative generation yet (also Phase 3) - just the state transition. This unblocks tension adjustment, character update suggestions, and generally completes the gameplay loop.

**Requirements:** REQ-SCENE-002, REQ-ACT-002 (without AI nudge portions, which remain in Phase 3)

---

### Step 27: AI Usage Tracking

Every AI call is logged with: the feature that triggered it (oracle, prose expansion, etc.), input and output token counts, context components included (world doc, characters, recent beats, etc.), model used, and timestamp. Data is queryable for analysis but not exposed to players in v1. Available to system administrators.

Implemented here, before the AI-heavy Phase 2 steps, so all subsequent features are built with logging from the start.

**Requirements:** REQ-AI-002

---

### Step 28: Tension Adjustment on Scene Completion

When a scene completes, the AI evaluates what happened and proposes whether tension should go up 1, down 1, or stay the same, with a transparent explanation. The AI accounts for scene outcome, recent narrative arc (sustained low/high tension), the fortune-roll feedback loop (low tension biases rolls favorably), and extreme-value correction (bias toward center when tension is already very high or very low).

Players each vote their own preferred delta (+1, 0, -1) after reading the AI's reasoning — not just accept/reject. Plurality wins; ties and abstentions fall back to the AI's suggestion. Proposals expire after the game's silence timer window; the AI suggestion is applied automatically if no votes are cast. Single-player games skip the vote and auto-apply. The adjustment is clamped to 1-9 and carries forward to the next scene via existing logic.

**Requirements:** REQ-TENSION-002

---

### Step 29: Tension Influence on Oracle Tone

The current tension value is included in the oracle's AI prompt context. High tension (7-9) biases the AI toward dramatic, unexpected, escalating interpretations. Low tension (1-3) biases toward subtle, tension-building, seed-planting interpretations. Mid tension (4-6) is balanced. This is primarily a prompt engineering step - the oracle flow doesn't change, just the quality of what comes back.

**Requirements:** REQ-TENSION-004

---

### Step 30: Challenge System - Filing a Challenge

Any player can challenge a canon beat. They provide a reason (fictional inconsistency, not creative disagreement). The beat is marked "challenged" and visually flagged in the timeline. The original author receives a personal notification; all other game members receive a broadcast notification so everyone knows a challenge is active.

**Requirements:** REQ-CHALLENGE-001

---

### Step 31: Challenge System - Resolution

The original author can accept the challenge and revise the beat, or disagree, in which case it goes to a group vote. If the vote says revise, the beat re-enters the proposed state and goes through approval again. Tie-breaking follows game settings.

**Requirements:** REQ-CHALLENGE-002

---

### Step 32: Pacing - Consecutive Beat Limit + Contribution Visibility

After a configurable number of consecutive narrative beats from the same player (default 3), a gentle nudge appears. OOC events don't count toward the limit. Also: a lightweight display of each player's recent contribution frequency on the scene page, for social self-regulation rather than enforced turn-taking.

**Requirements:** REQ-PACE-001, REQ-PACE-002

---

### Step 33: Spotlight / Waiting for Response

A player can mark their beat as "waiting for response from [character]." The spotlighted player gets a notification and their character is highlighted in the UI. Others can still post OOC or interact with oracle results, but the narrative focus is held. The spotlight expires after the silence timer or when the spotlighted player responds.

**Requirements:** REQ-PACE-003

---

### Step 34: Character Voice Notes

Each character can have optional voice notes describing their narrative style (e.g., "terse and clipped," "flowery and introspective"). Stored on the character, used by the AI for prose expansion and narrative compilation. Defaults to empty, falling back to the game's default narrative voice.

**Requirements:** REQ-CHAR-002

---

### Step 35: Prose Expansion

After a player submits a beat with narrative events, the AI generates a polished prose version in the background using the game's narrative voice and the character's voice notes. Shown only to the author, inline beneath their original text. Author can use it, edit it, or dismiss it. Does not block submission or delay the beat lifecycle. Both the original text and the selected prose version (if any) are stored.

Players can configure their preference per account: always show suggestions (default), never show suggestions, or only suggest when text is under N words. Preference can be overridden per game.

**Requirements:** REQ-PROSE-001

---

### Step 36: AI Pre-submission Consistency Check

Before a beat is submitted, the AI checks it against the world document, recent beats, established character/NPC/world facts, current roll results (if the beat contains a roll), and lines and veils. Inconsistencies are flagged to the author privately before submission (e.g., "You rolled a partial success but this outcome reads like a full success" or "You established earlier that the warehouse is locked").

Advisory only - does not block submission. The player can revise or submit anyway.

**Requirements:** REQ-BEAT-005

---

### Step 37: AI-Suggested Character Updates

After a scene completes, the AI reviews recent beats and suggests additions to character sheets: new relationships, traits revealed through action, items acquired, goals changed. Suggestions are presented privately to the character's owning player. The player can accept, modify, or dismiss each suggestion. Accepted updates are added to the character document.

**Requirements:** REQ-CHAR-003

---

### Step 38: Fortune Roll Oracle Follow-up

When a Fortune Roll returns an Exceptional Yes or Exceptional No, Loom prompts: "That's an exceptional result - want the oracle to suggest what that means?" If the player accepts, the full interpretive oracle is invoked with the Fortune Roll question as context, the exceptional result as a constraint, and a word seed pair generated for inspiration. The player can decline and interpret the exceptional result themselves.

Regular Yes/No results do not trigger the prompt, though the player can always invoke the oracle manually afterward.

**Requirements:** REQ-ORACLE-008

---

### Step 39: Email Notifications

Email notifications for the same events as in-app notifications. Players can configure email notification preferences: immediate (every event), digest (batched at configurable frequency, e.g., every few hours or daily), or off. Default is digest.

Preferences configurable globally and overridable per game. Emails include a direct link to the relevant game/scene/beat.

**Requirements:** REQ-NOTIFY-002
