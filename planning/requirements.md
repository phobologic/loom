# Loom - Requirements Document

## Product Overview

Loom is an async-first web application for collaborative, GM-less tabletop roleplaying. Rather than replacing the GM with AI, Loom treats all players (2-5) as co-GMs who share narrative authority equally. AI serves as a creative assistant - generating oracle interpretations, expanding shorthand into prose, tracking world details, and nudging the story forward - but never makes decisions for the players.

The core design philosophy: keep the fiction moving, make collaboration lightweight, and let the polished narrative emerge as a byproduct of play rather than a task anyone has to manage.

### Key Design Principles

- **Async-first**: Every interaction is designed for players who check in at different times throughout the day. Synchronous play is possible but not the primary mode.
- **Silence is consent**: If no one objects within a configurable time window, proposed content becomes canon. This prevents async games from stalling.
- **Player authority**: The player who acts (rolls, proposes) gets the final say on their own beats, informed by group input and AI suggestions. The group's authority is exercised through voting on major beats, challenges, and collaborative framing.
- **Bullets over prose**: Players should never feel pressured to write polished text. Quick shorthand is always acceptable; the AI can expand it later.
- **Progressive disclosure**: New groups get scaffolding and guidance. Experienced groups can skip what they don't need.

### Data Model Overview

```
Game (settings, world document, members, active word seed tables)
  Act (guiding question, status, narrative)
    Scene (guiding question, characters present [dynamic], location, status, narrative, tension)
      Beat (author, significance, status/lifecycle, embedded events)
        Event (type: narrative | roll | oracle | fortune_roll | ooc)
  Character (owned by a player, living document)
  NPC (shared, living document)
  WorldEntry (shared, wiki-like entries for locations, factions, items, etc.)
  WordSeedTable (action words and descriptor words, by genre/theme)
```

### Glossary

**Act** - A major narrative arc within a game, similar to an act in a play or a chapter in a book. Each act is driven by a guiding question (e.g., "Who is behind the disappearances?") and is made up of one or more scenes. When the guiding question is answered, the act is complete.

**Beat** - The core unit of play. A beat is a moment of change in the fiction, submitted by a single player. A beat contains one or more events and has a lifecycle: it's classified as major or minor, submitted, and either becomes canon immediately (minor) or goes through group approval (major). Beats can be challenged after the fact.

**Canon** - The accepted, official state of the fiction. A minor beat becomes canon the instant it's submitted. A major beat becomes canon when the group approves it (or the silence timer expires without objection).

**Challenge** - A mechanism for any player to flag a canon beat as inconsistent with the established fiction. The original author can revise, or the group votes on whether the beat stands. Challenges are for genuine fictional inconsistencies, not creative disagreements.

**Characters Present** - A dynamic, point-in-time list of which characters are currently in the active scene. Updated automatically as characters enter and leave. Used by the AI to ensure oracle suggestions and prose only reference characters who are actually there.

**Event** - An atomic piece of content within a beat. Events have types: narrative (in-character action, description, or dialogue), roll (a dice roll with result), oracle (an oracle query and its interpretations), fortune_roll (a yes/no Fortune Roll and its result), and ooc (out-of-character comment or discussion).

**Fortune Roll** - A quick yes/no oracle for narrative questions where no game system mechanic applies. The player asks a question (e.g., "Does someone show up?"), sets the odds (from Impossible to Near Certain), and Loom rolls against a probability table modified by the current Tension. Results range from Exceptional No to Exceptional Yes. Not to be used for character skill checks - those go through the group's chosen game system.

**Game** - The top-level container for a campaign or story. A game has members (2-5 players), settings, a world document, and contains acts, characters, NPCs, and world entries.

**Guiding Question** - A question attached to each act and scene that defines its narrative purpose. "What does the data fragment reveal?" or "Who is behind the conspiracy?" The guiding question helps players stay focused and helps the AI detect when a scene or act might be ready to complete.

**Major Beat** - A beat classified as significant enough to require group approval before becoming canon. Examples: introducing a major NPC, revealing important information, changing established world facts. The AI suggests whether a beat is major or minor, and the submitting player accepts or overrides.

**Minor Beat** - A beat classified as routine or low-impact, which becomes canon immediately on submission with no approval required. Examples: describing a character's actions, reacting to established events, entering an already-anticipated scene. Can still be challenged after the fact.

**NPC** - A non-player character tracked as a shared, living document. NPCs can be created manually or suggested by the AI when new named characters appear in the fiction.

**Oracle (Interpretive)** - Loom's AI-powered creative suggestion tool. A player asks an open-ended question (e.g., "What goes wrong?"), Loom generates word seeds and multiple narrative interpretations, and the group discusses and selects one. The invoking player makes the final choice.

**Organizer** - The player who created the game. Has administrative privileges (adjusting settings, removing players, pausing the game) but no special narrative authority. Cannot override votes, auto-approve beats, or skip challenges.

**Prose Expansion** - An optional AI feature that generates a polished prose version of a player's shorthand or bullet-point narrative. Generated in the background after submission and shown only to the author, who can use it, edit it, or dismiss it. Never blocks submission.

**Scene** - A specific situation, location, or encounter within an act, driven by its own guiding question. Scenes contain beats and track which characters are currently present. When the guiding question is answered, the scene is complete.

**Session 0** - The collaborative setup process at the start of a game where players establish the setting, tone, themes, content boundaries, word seed tables, characters, and the first act/scene. Guided by structured prompts with AI synthesis, but players can exit early when they feel ready.

**Silence Timer** - The configurable window (default: 12 hours) during which players can vote on major beats and proposals. If the timer expires without enough objections to block, the proposal auto-approves. Only applies to major beats and proposals - minor beats are canon immediately.

**Spotlight** - An optional indicator a player can set on their beat to signal that they're waiting for a specific character to respond. The spotlighted player gets a notification. Other players can still post OOC or interact with oracle results, but the narrative focus is held.

**Tension** - A per-scene value (1-9, starting at 5) that tracks narrative intensity and pacing. Higher tension tips Fortune Roll probabilities toward "Yes" and exceptional results, and biases the oracle toward more dramatic suggestions. Lower tension favors subtler, tension-building outcomes. Adjusted at scene completion based on AI evaluation of what happened, with group confirmation.

**Word Seeds** - A pair of randomly generated words (one action/verb, one descriptor/subject) used as creative constraints for the interpretive oracle. Drawn from genre-appropriate tables selected during Session 0. Displayed to all players alongside oracle results so everyone can see what inspired the suggestions.

**World Document** - The shared reference document produced during Session 0 that captures the agreed-upon setting, tone, themes, and boundaries. Used as context for all AI features throughout play.

**World Entry** - A shared, wiki-like entry for a location, faction, item, or other notable element of the game world. Can be created manually or suggested by the AI as new elements appear in the fiction.

---

## 1. User Accounts and Authentication

### REQ-AUTH-001: OAuth Authentication
*Requirement:* Loom shall support user authentication via OAuth providers, starting with Google and Discord.
*Acceptance Criteria:*
- Users can sign in using their Google account.
- Users can sign in using their Discord account.
- No email/password authentication is required for v1.
- A new user account is created automatically on first OAuth sign-in.
- Users have a display name (editable) and a unique internal ID.

### REQ-AUTH-002: User Profile
*Requirement:* When a user has authenticated, Loom shall provide a user profile where they can set their display name and manage their account.
*Acceptance Criteria:*
- Users can set and update a display name.
- Users can see which games they belong to.
- Users can configure their notification preferences (see REQ-NOTIFY).

---

## 2. Game Management

### REQ-GAME-001: Game Creation
*Requirement:* When a user wants to start a new game, Loom shall allow them to create a game with a name and an initial pitch or description.
*Acceptance Criteria:*
- The creator provides a game name (required) and a pitch/description (optional).
- The creator becomes a member of the game with the "organizer" role.
- The game is private by default.
- The game is created in a "setup" state, ready for Session 0.

### REQ-GAME-002: Game Invitation
*Requirement:* When a game has been created, Loom shall generate a shareable invite link that the organizer can distribute to other players.
*Acceptance Criteria:*
- The invite link is unique to the game.
- Any authenticated user with the link can join the game, up to 5 total players.
- Loom rejects joins that would exceed 5 players.
- The organizer can regenerate or revoke the invite link.

### REQ-GAME-003: Game Organizer Role
*Requirement:* The game creator shall have an "organizer" role with administrative (but not narrative) privileges.
*Acceptance Criteria:*
- The organizer can adjust game settings (timers, voting thresholds, tie-breaking rules, significance defaults) after creation.
- The organizer can remove a player from the game.
- The organizer can pause or archive a game.
- The organizer has no special narrative authority - they cannot override votes, auto-approve their own beats, or skip challenges.
- All organizer actions are visible to all players.

### REQ-GAME-004: Game Settings
*Requirement:* Loom shall provide configurable settings per game, with sensible defaults.
*Acceptance Criteria:*
- Configurable settings include:
  - Silence timer duration (default: 12 hours) - how long before uncontested major beats auto-approve.
  - Voting threshold: majority of all players (default, non-configurable formula, but the timer is adjustable).
  - Tie-breaking method (options: random/die roll, proposer decides, challenger decides; default: random).
  - Beat significance threshold (options: flag most things as major, only flag obvious things, minimal flagging; default: only flag obvious things).
  - Maximum consecutive beats per player before soft spotlight nudge (default: 3).
  - Auto-generate narrative on scene/act completion (default: on).
  - Fortune Roll odds contestation window (default: half the silence timer or 1 hour minimum).
  - Starting Tension for new acts (default: 5).
- Settings can be changed by the organizer at any time.
- Changes to settings are visible to all players.

### REQ-GAME-005: Game States
*Requirement:* Loom shall track game state through a defined lifecycle.
*Acceptance Criteria:*
- Game states: setup (Session 0 in progress), active (play in progress), paused, archived.
- Only the organizer can pause or archive a game.
- A paused game can be resumed by the organizer.
- An archived game is read-only but still viewable.

---

## 3. Session 0 - Collaborative World Building

### REQ-S0-001: Session 0 Flow
*Requirement:* When a game is in the "setup" state, Loom shall guide players through a collaborative Session 0 process to establish the shared fiction.
*Acceptance Criteria:*
- The flow consists of a structured sequence of prompts covering: genre, tone, setting, central tension/mystery, themes, and safety tools (lines and veils).
- The game creator's initial pitch/description is presented as a starting point.
- Players can skip, reorder, or add custom prompts.
- Each prompt allows all players to contribute ideas.

### REQ-S0-002: AI Synthesis During Session 0
*Requirement:* When players provide input during Session 0 prompts, Loom shall use AI to synthesize contributions into coherent proposals.
*Acceptance Criteria:*
- The AI reads all player contributions for a given prompt and generates a synthesized version (e.g., "Three of you mentioned noir elements, one mentioned fantasy - here are some ways those could combine").
- Players can accept, modify, or request regeneration of the AI synthesis.
- The AI provides suggestions and guidance throughout the process to help groups that are unsure.

### REQ-S0-003: World Document
*Requirement:* When Session 0 prompts have been completed, Loom shall produce a world document that captures the agreed-upon setting, tone, themes, and boundaries.
*Acceptance Criteria:*
- The world document is generated by the AI based on all Session 0 inputs.
- All players can review and suggest edits to the world document.
- The group approves the world document via the standard voting mechanism.
- The world document is available for reference throughout play.
- The world document is used as context for all AI features (oracle, prose expansion, etc.).

### REQ-S0-004: Narrative Voice
*Requirement:* During Session 0, Loom shall allow the group to establish a default narrative voice for AI-generated prose.
*Acceptance Criteria:*
- The AI offers sample narrative voice options based on the chosen genre/tone (e.g., terse noir, lyrical fantasy, dry humor).
- The group selects or customizes a default voice.
- The chosen voice is stored as part of the game configuration and used for all prose expansion and narrative compilation.

### REQ-S0-005: Early Exit from Session 0
*Requirement:* When all players agree they have enough to start playing, Loom shall allow the group to exit Session 0 early and begin play.
*Acceptance Criteria:*
- Any player can propose "ready to play."
- If all players agree (standard voting), Loom finalizes whatever has been established so far into the world document and transitions the game to "active" state.
- Loom generates a world document from whatever has been completed, even if some prompts were skipped.
- Minimum requirement to exit: a game name and at least one sentence of setting/pitch exist.

### REQ-S0-006: Safety Tools
*Requirement:* During Session 0, Loom shall provide a way for players to establish content boundaries.
*Acceptance Criteria:*
- Players can define "lines" (hard limits - content that must not appear).
- Players can define "veils" (content that can be referenced but not depicted in detail - fade to black).
- Lines and veils are stored as part of the game configuration.
- Lines and veils are included in AI context so that oracle suggestions and prose expansion respect them.
- Any player can add new lines or veils at any time during play (not just Session 0).

---

## 4. Character Management

### REQ-CHAR-001: Character Creation
*Requirement:* When the world document has been established (or Session 0 has been exited), Loom shall allow each player to create a character.
*Acceptance Criteria:*
- Character creation happens after the setting is established, not before.
- Each player creates one character (with name, description, and optional personality/goal notes).
- Character information is visible to all players in the game.
- A player can edit their own character at any time.

### REQ-CHAR-002: Character Voice Notes
*Requirement:* Loom shall allow players to optionally define narrative voice preferences for their character.
*Acceptance Criteria:*
- Each character can have optional voice notes (e.g., "tense and clipped," "flowery and introspective").
- Voice notes are used by the AI when generating prose expansion or narrative compilation for scenes involving that character.
- Voice notes default to empty (the game's default narrative voice is used).

### REQ-CHAR-003: AI-Suggested Character Updates
*Requirement:* As play progresses, Loom shall use AI to suggest updates to character documents based on fictional events.
*Acceptance Criteria:*
- After a scene completes (or periodically during play), the AI reviews recent beats and suggests additions to character sheets (e.g., new relationships, traits revealed through action, items acquired, goals changed).
- Suggestions are presented privately to the character's owning player.
- The player can accept, modify, or dismiss each suggestion.
- Accepted updates are added to the character document.

---

## 5. NPC and World Entry Tracking

### REQ-NPC-001: NPC Creation and Tracking
*Requirement:* Loom shall track NPCs that appear in the fiction as shared, living documents.
*Acceptance Criteria:*
- Any player can manually create an NPC entry (name, description, notes).
- NPC entries are shared and visible to all players.
- Any player can edit any NPC entry.

### REQ-NPC-002: AI-Suggested NPC Entries
*Requirement:* When new NPCs appear in the fiction, Loom shall use AI to suggest creating entries for them.
*Acceptance Criteria:*
- The AI monitors beats for references to new named characters who are not existing PCs or NPCs.
- The AI suggests creating an NPC entry with a proposed name, description, and notes based on their appearances in the fiction.
- Any player can approve, modify, or dismiss the suggestion.

### REQ-WORLD-001: World Entry Tracking
*Requirement:* Loom shall support shared, wiki-like entries for locations, factions, items, and other world elements.
*Acceptance Criteria:*
- Any player can create a world entry with a name, type (location, faction, item, concept, other), and description.
- World entries are shared and visible to all players.
- Any player can edit any world entry.

### REQ-WORLD-002: AI-Suggested World Entries
*Requirement:* As play progresses, Loom shall use AI to suggest new world entries based on the fiction.
*Acceptance Criteria:*
- The AI monitors beats for references to new locations, organizations, or significant items that don't have existing entries.
- The AI suggests creating entries with proposed details based on context.
- Any player can approve, modify, or dismiss the suggestion.

### REQ-WORLD-003: Relationship Tracking
*Requirement:* Loom shall track relationships between characters, NPCs, and world entries.
*Acceptance Criteria:*
- Relationships can be created manually by any player (e.g., "Kira - rivals with - Dock Master Venn").
- The AI can suggest relationships based on fictional events.
- Relationships are visible on the relevant character/NPC/world entry pages.

---

## 6. Act and Scene Management

### REQ-ACT-001: Act Creation
*Requirement:* When the game is active, Loom shall allow players to propose a new act with a guiding question.
*Acceptance Criteria:*
- Any player can propose a new act.
- The proposal includes a title (optional) and a guiding question (required) - e.g., "Who is behind the disappearances in the Rusted Quarter?"
- Act creation is treated as a major beat and requires group approval via the standard voting mechanism.
- The AI can suggest possible guiding questions based on unresolved threads in the fiction.
- Only one act can be active at a time.

### REQ-ACT-002: Act Completion
*Requirement:* When players believe an act's guiding question has been answered or the narrative has reached a natural break, Loom shall support completing the act.
*Acceptance Criteria:*
- Any player can propose completing the current act.
- Completion requires group approval via the standard voting mechanism.
- On completion, the AI generates a narrative summary of the act (if auto-narrative is enabled in game settings).
- The act is marked as complete and becomes read-only.

### REQ-ACT-003: AI Nudge for Act Completion
*Requirement:* When the AI detects that an act's guiding question may have been answered, it shall suggest that the group consider completing the act.
*Acceptance Criteria:*
- The AI monitors the fiction for signals that the guiding question has been resolved.
- The suggestion is surfaced to all players as a non-blocking prompt.
- Players can dismiss the suggestion or initiate the completion proposal.
- The AI does not auto-complete acts.

### REQ-SCENE-001: Scene Creation
*Requirement:* When an act is active, Loom shall allow players to propose a new scene.
*Acceptance Criteria:*
- Any player can propose a new scene within the active act.
- The proposal includes: a title (optional), a description (optional), a guiding question (required) - e.g., "Can we convince the dock master to let us into the warehouse?", which characters are present (required), and a location (optional, can reference an existing world entry or create a new one).
- Scene creation is treated as a major beat and requires group approval.
- The AI can suggest possible next scenes based on where the fiction left off, including proposed guiding questions.
- Multiple scenes cannot be active simultaneously in v1.

### REQ-SCENE-002: Scene Completion
*Requirement:* When players believe a scene's guiding question has been answered, Loom shall support completing the scene.
*Acceptance Criteria:*
- Any player can propose completing the current scene.
- Completion requires group approval via the standard voting mechanism.
- On completion, the AI generates a narrative for the scene (if auto-narrative is enabled).
- The scene is marked as complete and becomes read-only.

### REQ-SCENE-003: AI Nudge for Scene Completion
*Requirement:* When the AI detects that a scene's guiding question may have been answered, it shall suggest that the group consider completing the scene.
*Acceptance Criteria:*
- The AI monitors the fiction for signals that the guiding question has been resolved.
- The suggestion is surfaced to all players as a non-blocking prompt.
- Players can dismiss the suggestion or initiate the completion proposal.

### REQ-SCENE-004: Scene Character Presence
*Requirement:* Loom shall track which characters are currently present in an active scene as a dynamic, point-in-time list.
*Acceptance Criteria:*
- When a scene is created, the proposer specifies which characters are initially present.
- The "Characters Present" list is a living indicator of who is in the scene *right now*, not a historical record of everyone who has ever been in the scene.
- When a character enters the scene (via a narrative beat), Loom updates the list to include them.
- When a character leaves the scene (via a narrative beat), Loom updates the list to remove them.
- Any player can update the presence list for their own character. Updating presence for NPCs or other players' characters follows the normal beat proposal flow.
- The Characters Present list is visible to all players at all times alongside the scene information.
- The Characters Present list is included in the AI context for oracle queries, prose expansion, and other AI features, so that suggestions only reference characters who are actually in the scene.
- The full history of who was present and when is derivable from the beat timeline and does not need separate tracking.

---

## 7. Beats and Events - Core Play Loop

### REQ-BEAT-001: Beat Submission
*Requirement:* When a scene is active, Loom shall allow any player to submit a beat.
*Acceptance Criteria:*
- A beat is authored by a single player.
- A beat contains one or more events (see REQ-EVENT).
- Players can write in shorthand/bullets - polished prose is never required.
- A beat is submitted as a proposal with a lifecycle (see REQ-BEAT-003).

### REQ-BEAT-002: Event Types
*Requirement:* Loom shall support the following event types within a beat.
*Acceptance Criteria:*
- **Narrative**: An in-character action, description, or dialogue (e.g., "I search the alley for signs of the courier").
- **Roll**: A dice roll with notation, result, and optional reason (see REQ-DICE).
- **Oracle**: An oracle query and its results (see REQ-ORACLE).
- **OOC**: An out-of-character comment, question, or discussion point.
- A single beat can contain multiple events of different types (e.g., a narrative action + a roll + an OOC note).
- Events within a beat are ordered.

### REQ-BEAT-003: Beat Lifecycle
*Requirement:* Loom shall manage beats through a defined lifecycle.
*Acceptance Criteria:*
- Beat statuses: proposed, canon, challenged, revised, rejected.
- When a minor beat is submitted, it becomes canon immediately. No approval gate or waiting period is required. Other players can challenge it after the fact if needed (see REQ-CHALLENGE).
- When a major beat is submitted, it enters "proposed" status and requires explicit approval via voting (see REQ-VOTE). The silence timer applies only to major beats.
- Any player can challenge a canon beat (see REQ-CHALLENGE), moving it to "challenged" status.
- A challenged beat can be revised by the original author (status: revised, then re-enters the approval flow as a major beat) or rejected by group vote.

### REQ-BEAT-004: Beat Significance Classification
*Requirement:* When a player submits a beat, Loom shall classify it as major or minor.
*Acceptance Criteria:*
- The AI analyzes the beat content and suggests a significance level based on factors such as: introducing a new named character, changing location, involving conflict or violence, revealing significant information, altering established world facts, or proposing a scene/act transition.
- The suggestion is shown to the submitting player before submission (e.g., "This seems like a major beat - put it up for group input?").
- The player can accept or override the AI's suggestion.
- The significance threshold is configurable per game (see REQ-GAME-004).
- Minor beats follow the silence-is-consent auto-approval path.
- Major beats require active voting.

### REQ-BEAT-005: AI Pre-submission Consistency Check
*Requirement:* Before a beat is submitted, Loom shall use AI to check it for consistency with established fiction.
*Acceptance Criteria:*
- The AI checks the beat against: the world document, recent beats, established character/NPC/world facts, the current roll result (if the beat contains a roll), and lines and veils.
- If inconsistencies are detected, they are flagged to the author privately before submission (e.g., "You rolled a partial success but this outcome reads like a full success" or "You established earlier that the warehouse is locked").
- The player can revise the beat or submit it anyway.
- This check is advisory only - it does not block submission.

### REQ-BEAT-006: Beat Timeline Display
*Requirement:* Loom shall display beats in a chronological timeline within each scene.
*Acceptance Criteria:*
- The timeline shows all beats in order of submission.
- Each beat displays: the author, the timestamp, the significance level, the current status, and all contained events.
- The timeline supports filtering by event type (show only IC content, show only OOC, show all).
- Beats with pending votes or active challenges are visually distinguished.

---

## 8. Dice Rolling

### REQ-DICE-001: Inline Dice Rolling
*Requirement:* Loom shall allow players to roll dice as part of a beat submission.
*Acceptance Criteria:*
- Players can include one or more dice rolls in a beat using standard notation (e.g., 2d6+1, 1d20, 3d10-2).
- The roll is executed server-side and the result is displayed as a roll event within the beat.
- The roll result is visible to all players.
- A reason/label can optionally be attached to each roll.

### REQ-DICE-002: Roll Interpretation by Players
*Requirement:* Loom shall leave interpretation of roll results to the players, not the AI.
*Acceptance Criteria:*
- Loom displays the numeric result but does not interpret success/failure or narrative outcome.
- Players interpret what the roll means in the fiction via narrative events within the same beat, subsequent beats, or by calling the oracle for suggestions.
- Loom does not enforce any specific game system's success criteria.

---

## 9. Oracle System

### REQ-ORACLE-001: Oracle Query
*Requirement:* When a player wants AI-generated suggestions for what happens next, Loom shall provide an oracle that generates interpretations based on the game's context.
*Acceptance Criteria:*
- Any player can invoke the oracle at any time during an active scene.
- The player provides a question or context (e.g., "What do I find in the alley?" or "Does the NPC betray us?") and optionally includes raw oracle/roll results to interpret.
- The oracle generates multiple interpretations (configurable count, default 3-5).
- Oracle queries can be embedded as an event within a beat.

### REQ-ORACLE-002: Oracle Context
*Requirement:* When the oracle is invoked, Loom shall provide the AI with rich context about the current game state.
*Acceptance Criteria:*
- Context includes: the world document, current act guiding question and summary, current scene guiding question and description, participating character descriptions, relevant NPC entries, relevant world entries, recent beat history, and lines and veils.
- Loom does not include all beats or all scenes - it provides overall context plus recent detail.
- Loom tracks token usage per oracle call for future optimization (see REQ-AI-002).

### REQ-ORACLE-003: Oracle Interaction Flow
*Requirement:* When oracle interpretations have been generated, Loom shall allow collaborative discussion and selection.
*Acceptance Criteria:*
- All players can see the generated interpretations.
- Players can vote on an interpretation.
- Players can comment on an interpretation (e.g., "I like #2 but what if the courier is already dead?").
- Players can propose their own alternative interpretation.
- The player who invoked the oracle makes the final selection, informed by votes, comments, and alternatives.
- If the oracle result affects only the invoking player's character (personal oracle), they can select without group input.
- If the oracle result affects the shared fiction (world oracle), the collaborative flow is used.

### REQ-ORACLE-004: Oracle Vote Tie-Breaking
*Requirement:* When oracle votes result in a tie, Loom shall resolve it according to the game's configured tie-breaking method.
*Acceptance Criteria:*
- Tie-breaking methods: random (roll a die between tied options - default), proposer decides, challenger decides.
- The tie-breaking method is configurable per game.
- All tie-breaking methods are available as configuration options.

### REQ-ORACLE-005: Word Seed Oracle
*Requirement:* When the interpretive oracle is invoked, Loom shall generate a random word pair to serve as a creative seed for the AI's interpretations.
*Acceptance Criteria:*
- Loom generates a pair of random words: one action/verb (e.g., "abandon," "betray," "protect") and one descriptor/subject (e.g., "mechanical," "dreams," "authority").
- The word pair is displayed to the player and the group before and alongside the oracle's interpretations, so players can see what creative constraint was used.
- The AI is instructed to weave the word pair's themes into its interpretations, using them as lateral inspiration rather than literal inclusion.
- The word pair is drawn from system-maintained word tables (not from any copyrighted source).
- The word tables should be extensible - Loom ships with a default general-purpose set, and genre-specific sets (e.g., horror, sci-fi, fantasy, noir) can be selected during Session 0 or added later.
- Players can optionally lock or re-roll the word pair before the oracle generates interpretations ("I don't like these seeds, give me new ones" or "These are perfect, go with these").
- The word pair and chosen interpretation are stored together for reference.

### REQ-ORACLE-006: Word Seed Tables
*Requirement:* Loom shall maintain word tables for use with the word seed oracle, organized by category.
*Acceptance Criteria:*
- Loom ships with a default set of action words (verbs/actions - e.g., "reveal," "abandon," "transform," "deceive") and descriptor words (subjects/modifiers - e.g., "ancient," "forbidden," "mechanical," "trust").
- Tables are organized by genre or theme (general, fantasy, sci-fi, horror, noir, etc.).
- During Session 0, the group selects which table sets are active for their game. Multiple sets can be active simultaneously (e.g., general + sci-fi).
- Custom words can be added to a game's active tables by any player, allowing the group to build a vocabulary that fits their specific setting.
- Loom uses the active tables when generating word pairs, drawing one word from the action table and one from the descriptor table at random.

### REQ-ORACLE-007: Fortune Roll (Yes/No Oracle)
*Requirement:* Loom shall provide a quick yes/no oracle for questions that don't need full narrative interpretations, using a weighted probability system.
*Acceptance Criteria:*
- Any player can ask a yes/no question and invoke a Fortune Roll instead of the full interpretive oracle.
- The asking player sets the odds for the question using a scale: Impossible, Very Unlikely, Unlikely, 50/50, Likely, Very Likely, Near Certain.
- Loom rolls against the probability, modified by the current Tension (see REQ-TENSION), and returns one of four results: Exceptional Yes, Yes, No, or Exceptional No.
- The result and the odds setting are displayed to all players.
- Other players can contest the odds setting before the roll resolves. If contested, the group discusses and the asking player adjusts or a quick vote settles the odds. To keep async play moving, if no one contests within a short window (configurable, default: half the silence timer or a minimum of 1 hour, whichever is greater), the roll resolves as set.
- Exceptional Yes and Exceptional No results are automatically flagged as major beats (they represent surprising or dramatic outcomes). Regular Yes and No results default to minor beats.
- A Fortune Roll can be embedded as an event within a beat, alongside narrative events.
- Word seeds (REQ-ORACLE-005) are not used for Fortune Rolls - they are a simple yes/no mechanism.

### REQ-ORACLE-008: Fortune Roll with Oracle Follow-up
*Requirement:* When a Fortune Roll returns an Exceptional result, Loom shall offer to invoke the full interpretive oracle to explore what the exceptional outcome means.
*Acceptance Criteria:*
- On an Exceptional Yes or Exceptional No, Loom prompts: "That's an exceptional result - want the oracle to suggest what that means?"
- If the player accepts, the full interpretive oracle (REQ-ORACLE-001) is invoked with the Fortune Roll question as context, the exceptional result as a constraint, and a word seed pair generated for additional inspiration.
- The player can decline and interpret the exceptional result themselves instead.
- Regular Yes/No results do not trigger this prompt, though a player can always manually invoke the full oracle afterward.

### REQ-TENSION-001: Tension Tracking
*Requirement:* Loom shall track a Tension per scene that represents the current level of narrative tension and unpredictability.
*Acceptance Criteria:*
- The Tension is a value from 1 to 9, starting at 5 for the first scene of a game.
- The current Tension is visible to all players at all times (displayed alongside the scene information).
- The Tension carries forward from scene to scene within an act. When a new scene begins, it inherits the Tension from the previous scene, as adjusted at that scene's completion.
- When a new act begins, the Tension resets to 5.

### REQ-TENSION-002: Tension Adjustment
*Requirement:* When a scene is completed, Loom shall propose a Tension adjustment based on what happened during the scene.
*Acceptance Criteria:*
- The AI evaluates the completed scene and proposes whether tension should increase (things spiraled, plans failed, new threats emerged, surprises dominated), decrease (players achieved their goals, resolved tensions, maintained control), or stay the same (mixed results, roughly balanced).
- The AI also considers the recent narrative arc (sustained low or high tension across multiple scenes) and the tension feedback loop (low tension biases fortune rolls favorably, which can perpetuate low-tension play). These arc-level factors can influence the recommendation even when the scene outcome alone is ambiguous.
- The AI applies an extreme-value correction: if tension is already 8 or above, it biases toward -1 unless the scene was clearly escalating; if tension is 3 or below, it biases toward +1 unless the scene was clearly resolving.
- The AI's proposal is shown to all players with a transparent explanation that explicitly names which factors (scene outcome, arc, feedback loop, extreme correction) drove the recommendation (e.g., "The security patrol, the data core crash, and the unresolved mystery of Deck 0 all point toward rising tension. Suggested adjustment: Tension +1, from 5 to 6.").
- Players each vote their own preferred delta (+1, 0, or -1) after reading the AI's reasoning. The plurality delta wins. If votes are tied or no one votes, the AI's suggestion is used.
- If no vote is cast within the game's silence timer window, the AI's suggestion is applied automatically.
- In single-player games, the AI's suggestion is applied immediately without a vote.
- The adjustment is always exactly +1, -1, or 0 - no larger jumps.
- The Tension cannot go below 1 or above 9.

### REQ-TENSION-003: Tension Effects on Fortune Roll
*Requirement:* The Tension shall modify the probability of Fortune Roll results.
*Acceptance Criteria:*
- Higher tension increases the probability of "Yes" answers and exceptional results, representing a world where more things happen and surprises are more frequent.
- Lower tension decreases the probability of "Yes" answers and exceptional results, representing a more controlled, predictable situation.
- The specific probability curve is calibrated so that: at Tension 1, even "Likely" questions have a meaningful chance of "No"; at Tension 5 (baseline), probabilities match the stated odds intuitively; at Tension 9, even "Unlikely" questions have a real chance of "Yes," and exceptional results are common.
- The probability table is documented and transparent to players (not a hidden mechanic).

### REQ-TENSION-004: Tension Effects on Interpretive Oracle
*Requirement:* The Tension shall influence the tone and nature of interpretive oracle suggestions.
*Acceptance Criteria:*
- When the interpretive oracle generates options, the current Tension is included in the AI's prompt context.
- At high tension (7-9), the AI is instructed to favor dramatic, unexpected, and complicating interpretations - twists, betrayals, escalations, unintended consequences.
- At mid tension (4-6), the AI provides a balanced mix of outcomes.
- At low tension (1-3), the AI is instructed to favor tension-building interpretations - subtle foreshadowing, quiet complications, things that plant seeds for future drama rather than exploding immediately.
- This influence is a bias, not an absolute - even at high tension, the oracle can suggest a calm outcome if it fits, and even at low tension, something dramatic can happen.

### REQ-TENSION-005: Random Events Triggered by High Tension
*Requirement:* When the Tension is high, Loom shall occasionally introduce unexpected random events to the scene.
*Acceptance Criteria:*
- At the start of each new scene, Loom rolls to determine if the scene is altered or interrupted based on the current Tension. Higher tension means higher probability of disruption.
- An "altered" scene means the AI suggests a modification to the proposed scene setup (something is different from what the players expected). The suggestion is shown to the group, who can accept, modify, or reject it.
- An "interrupted" scene means the AI suggests an entirely different scene driven by a random event, using a word seed pair for inspiration. The group can accept (replacing their proposed scene), weave it in (modifying their proposed scene to include the interruption), or reject it (proceeding as planned, but the rejected event is noted as a potential future thread).
- Additionally, during play, when a Fortune Roll rolls doubles and the individual digit is equal to or less than the current Tension, a random event is triggered alongside the Fortune Roll result. The AI generates a brief complication or twist using a word seed pair and the current context.
- Random events triggered during play are presented as suggestions to the group, not forced into the fiction. They follow the standard beat proposal and approval flow.
- At low tension (1-3), random events are very rare. At high tension (7-9), they are frequent and disruptive.

---

## 10. Voting and Approval

### REQ-VOTE-001: Voting Mechanics
*Requirement:* When a major beat, scene transition, act transition, or other significant proposal is submitted, Loom shall manage a voting process.
*Acceptance Criteria:*
- The proposer's submission counts as an implicit "yes" vote.
- The threshold for approval is more than half of all players in the game (e.g., in a 3-player game, 2 votes needed; in a 4-player game, 3 votes needed; in a 5-player game, 3 votes needed).
- In a 2-player game, the other player must explicitly approve major proposals.
- Players can vote yes, no, or suggest a modification.
- Votes and suggestions are visible to all players.

### REQ-VOTE-002: Silence is Consent
*Requirement:* When a major beat or other proposal requiring a vote has been open for the configured silence timer duration without reaching a rejection threshold, Loom shall auto-approve it.
*Acceptance Criteria:*
- This applies to major beats, scene/act proposals, and other items that go through the voting flow. Minor beats are canon immediately and do not use the silence timer.
- The silence timer is configurable per game (default: 12 hours).
- If the timer expires and the proposal has not been explicitly rejected by enough players to block it, it is automatically approved and moves to canon status.
- Players are notified when auto-approval occurs.
- The timer resets if a modification is suggested (giving the proposer time to revise).

---

## 11. Challenge System

### REQ-CHALLENGE-001: Challenging a Beat
*Requirement:* When a player believes a canon beat contradicts the established fiction, Loom shall allow them to challenge it.
*Acceptance Criteria:*
- Any player can challenge any canon beat at any time.
- The challenger must provide a reason (e.g., "This contradicts the established magic system" or "A partial success shouldn't result in this outcome").
- The challenged beat is marked as "challenged" and visually flagged in the timeline.
- The original author is notified of the challenge with a personal notification.
- All other game members receive a broadcast notification so everyone is aware a challenge is active.

### REQ-CHALLENGE-002: Challenge Resolution
*Requirement:* When a beat has been challenged, Loom shall facilitate resolution.
*Acceptance Criteria:*
- The original author can accept the challenge and revise the beat.
- If the original author disagrees, the challenge goes to a group vote.
- The vote determines whether the beat stands as-is or must be revised.
- Tie-breaking follows the game's configured tie-breaking method.
- If the beat must be revised, it re-enters the proposed state and goes through the approval flow again.

---

## 12. Spotlight and Pacing

### REQ-PACE-001: Consecutive Beat Limit
*Requirement:* When a player has posted multiple consecutive narrative beats, Loom shall nudge them to allow others to contribute.
*Acceptance Criteria:*
- After a configurable number of consecutive narrative beats from the same player (default: 3), Loom displays a gentle nudge: "You've posted the last N beats - maybe see if others want to jump in?"
- The nudge is a suggestion, not a hard block. The player can continue posting if the fiction demands it.
- OOC events do not count toward the consecutive beat limit.
- The limit is configurable per game.

### REQ-PACE-002: Contribution Visibility
*Requirement:* Loom shall make each player's contribution frequency visible to the group.
*Acceptance Criteria:*
- Loom tracks how many narrative beats each player has contributed recently (within the current scene or a rolling window).
- This information is displayed in a lightweight, non-judgmental way (e.g., a simple bar or indicator visible on the scene page).
- The intent is to enable social self-regulation, not to enforce strict turn-taking.

### REQ-PACE-003: Waiting for Response
*Requirement:* When a player submits a beat that invites a response from a specific character, Loom shall support a "waiting for" indicator.
*Acceptance Criteria:*
- A player can optionally mark their beat as "waiting for response from [character]."
- The spotlighted player's character is highlighted in the UI.
- The spotlighted player receives a notification.
- Other players can still post OOC events or interact with oracle results, but the narrative focus is held on the spotlighted character.
- The spotlight expires after the silence timer or when the spotlighted player responds.

---

## 13. Prose Expansion and Narrative

### REQ-PROSE-001: Beat-Level Prose Expansion
*Requirement:* When a player submits a beat containing narrative events, Loom shall generate a prose expansion after submission and offer it to the author inline without blocking the submission flow.
*Acceptance Criteria:*
- The player's original text is submitted immediately. For minor beats, it becomes canon instantly. For major beats, it enters the voting flow. Prose expansion does not delay either path.
- After submission, Loom generates a prose-expanded version in the background, using the game's established narrative voice and the character's voice notes (if any).
- The prose suggestion is shown only to the authoring player, displayed inline beneath their original text.
- The player can: use the suggested prose (replacing their original in the timeline), edit the suggested prose before applying it, or dismiss the suggestion (their original text remains unchanged).
- If the player applies a prose version, other players see the updated text with a subtle "edited" indicator. For major beats already in the voting flow, the content updates in place without restarting the vote.
- Both the original text and the selected prose version (if any) are stored.
- Players can configure their prose suggestion preference per account: "Always show suggestions" (default), "Never show suggestions," or "Only suggest when my text is under N words" (for players who write detailed prose and don't need expansion on longer entries).
- This preference can be overridden per game if desired.

### REQ-PROSE-002: Scene Narrative Compilation
*Requirement:* When a scene is completed, Loom shall generate a compiled narrative for the scene.
*Acceptance Criteria:*
- If auto-narrative is enabled in game settings, the AI generates a prose narrative for the completed scene.
- The narrative is based on all narrative and roll events within the scene's beats, using the game's narrative voice and character voice notes.
- OOC events are excluded from the narrative.
- The narrative is stored with the scene and viewable by all players.
- The narrative is read-only in v1 (no collaborative editing).

### REQ-PROSE-003: Act Narrative Compilation
*Requirement:* When an act is completed, Loom shall generate a compiled narrative for the act.
*Acceptance Criteria:*
- If auto-narrative is enabled, the AI generates a prose narrative for the completed act, incorporating scene narratives and the act's overall arc.
- The act narrative uses the act's guiding question and resolution as framing.
- The narrative is stored with the act and viewable by all players.
- The narrative is read-only in v1.

### REQ-PROSE-004: Narrative Export
*Requirement:* Loom shall allow players to export narratives in markdown format.
*Acceptance Criteria:*
- Players can export individual scene narratives, individual act narratives, or a combined export of all completed act narratives in sequence.
- Export format is markdown.
- The export includes act and scene titles and guiding questions as structural headers.

---

## 14. Notifications

### REQ-NOTIFY-001: In-App Notifications
*Requirement:* Loom shall display in-app notifications for game activity requiring player attention.
*Acceptance Criteria:*
- Notifications are generated for: new beats in your game, votes requiring your input, oracle interpretations ready for review, challenges to your beats, spotlight/waiting-for-you indicators, AI suggestions (character updates, NPC entries, world entries, scene/act completion nudges), and auto-approval events.
- Unread notification count is visible on the game list and within each game.
- Notifications can be marked as read individually or in bulk.

### REQ-NOTIFY-002: Email Notifications
*Requirement:* Loom shall send email notifications for game activity to prevent async games from stalling.
*Acceptance Criteria:*
- Email notifications are sent for the same events as in-app notifications.
- Players can configure email notification preferences: immediate (every event), digest (batched, configurable frequency - e.g., every few hours or daily), or off.
- Default email preference is digest.
- Players can configure notification preferences globally and override per game.
- Emails include a direct link to the relevant game/scene/beat.

---

## 15. AI Integration

### REQ-AI-001: AI Provider Abstraction
*Requirement:* Loom shall abstract AI interactions behind a generic interface so that the underlying provider can be changed without affecting the rest of Loom.
*Acceptance Criteria:*
- All AI calls go through a common interface/abstraction layer.
- The initial implementation uses Anthropic's API (Claude).
- Switching to a different provider requires changes only in the provider implementation, not in calling code.
- The interface supports: text generation (for oracle, prose expansion, narrative compilation, Session 0 synthesis), classification (for beat significance, consistency checking), and suggestion generation (for character/NPC/world updates, scene/act completion nudges).

### REQ-AI-002: AI Usage Tracking
*Requirement:* Loom shall track AI usage for monitoring and future optimization.
*Acceptance Criteria:*
- Every AI call is logged with: the feature that triggered it (oracle, prose expansion, etc.), input token count, output token count, the context components included (world doc, characters, recent beats, etc.), and a timestamp.
- Usage data is queryable for analysis (e.g., average tokens per oracle call, most expensive features).
- Usage data is not exposed to players in v1 but is available for system administrators.

### REQ-AI-003: AI Context Assembly
*Requirement:* When assembling context for any AI call, Loom shall include relevant game state without sending the entire game history.
*Acceptance Criteria:*
- Standard context includes: world document, current act guiding question, current scene guiding question and description, characters currently present in the scene, relevant NPC entries, recent beat history (configurable window), and lines and veils.
- Loom avoids sending all beats or all scenes.
- Context is assembled fresh for each call to reflect the current game state.
- Lines and veils are always included and the AI is instructed to respect them.

### REQ-AI-004: Model Configuration Per Feature
*Requirement:* Loom shall allow configuration of which AI model is used for each type of AI interaction, enabling cost and quality optimization.
*Acceptance Criteria:*
- Each AI feature is mapped to a configurable model selection. Features include: beat significance classification (major/minor), pre-submission consistency checking, oracle interpretive generation, Fortune Roll exceptional result follow-up, prose expansion, scene/act narrative compilation, Session 0 synthesis, character/NPC/world update suggestions, scene/act completion nudge detection, and Tension adjustment evaluation.
- Default model assignments balance cost and quality. Lightweight tasks (classification, nudge detection, significance assessment) default to a smaller/cheaper model (e.g., Haiku). Creative and nuanced tasks (oracle interpretation, prose expansion, narrative compilation, Session 0 synthesis) default to a more capable model (e.g., Sonnet).
- Model assignments are configurable by system administrators, not by individual players or game organizers (to prevent cost surprises).
- Model assignment changes take effect on new AI calls without requiring a restart.
- The AI usage tracking (REQ-AI-002) records which model was used for each call, enabling cost analysis per feature and per model.

---

## 16. Technical Requirements

### REQ-TECH-001: Technology Stack
*Requirement:* Loom shall be built with the following technology stack.
*Acceptance Criteria:*
- Backend: Python with FastAPI.
- Templating: Jinja2 for server-rendered pages.
- Frontend interactivity: HTMX for dynamic behavior without a JavaScript framework.
- Database: PostgreSQL (AWS Aurora for production, local PostgreSQL for development/testing).
- ORM: SQLAlchemy with Alembic for migrations.
- AI: Anthropic API via abstraction layer (see REQ-AI-001).
- Authentication: OAuth via Google and Discord.

### REQ-TECH-002: API Design
*Requirement:* Loom shall expose API endpoints alongside server-rendered views to support future frontend development.
*Acceptance Criteria:*
- All data-mutating operations are available as API endpoints (JSON in/out).
- Server-rendered pages call the same underlying logic as the API endpoints.
- API endpoints are documented (FastAPI auto-generates OpenAPI docs).

### REQ-TECH-003: Database Design
*Requirement:* Loom shall implement the data model as described in the Product Overview, using SQLAlchemy models.
*Acceptance Criteria:*
- All entities (Game, Act, Scene, Beat, Event, Character, NPC, WorldEntry, Relationship, WordSeedTable) are represented as SQLAlchemy models.
- Migrations are managed with Alembic.
- Foreign key relationships and cascading deletes are properly configured.
- All models include created_at and updated_at timestamps.
- The Beat model includes: author (FK to user), significance (major/minor), status (proposed/approved/canon/challenged/revised/rejected), and a relationship to multiple Events.
- The Event model includes: type (narrative/roll/oracle/fortune_roll/ooc), content, ordering within the beat, and type-specific fields (e.g., dice notation and result for roll events, oracle query and interpretations for oracle events, odds setting and tension level for fortune_roll events, word seed pair for oracle/fortune_roll events).
- The Scene model includes a tension integer field (1-9).
- The WordSeedTable model includes: a name, a genre/theme tag, a type (action or descriptor), and a list of words. Games have a many-to-many relationship with active WordSeedTables.

### REQ-TECH-004: Local Development
*Requirement:* Loom shall support local development with minimal setup.
*Acceptance Criteria:*
- Developers can run the full application locally with a local PostgreSQL instance.
- A docker-compose or equivalent setup is provided for local dependencies.
- Environment variables or a local configuration file manage settings for different environments.
- Tests can run against a local/test database.

---

## Priority and Phasing

### Phase 1 - Core Loop
REQ-AUTH-001, REQ-AUTH-002, REQ-GAME-001 through REQ-GAME-005, REQ-S0-001 through REQ-S0-006, REQ-CHAR-001, REQ-ACT-001, REQ-SCENE-001, REQ-SCENE-004, REQ-BEAT-001 through REQ-BEAT-006, REQ-DICE-001, REQ-DICE-002, REQ-ORACLE-001 through REQ-ORACLE-007, REQ-TENSION-001, REQ-TENSION-003, REQ-VOTE-001, REQ-VOTE-002, REQ-NOTIFY-001, REQ-AI-004, REQ-TECH-001 through REQ-TECH-004.

This delivers: create a game, run Session 0, create characters, frame acts and scenes with dynamic character presence tracking, post beats with events, roll dice, use the interpretive oracle with word seeds and voting, use the Fortune Roll (yes/no oracle) with basic Tension influence on probabilities, in-app notifications, and per-feature AI model configuration. The minimum viable play experience.

### Phase 2 - Polish and Safety
REQ-CHALLENGE-001, REQ-CHALLENGE-002, REQ-BEAT-005 (AI consistency check), REQ-PACE-001 through REQ-PACE-003, REQ-PROSE-001, REQ-CHAR-002, REQ-CHAR-003, REQ-NOTIFY-002, REQ-AI-002, REQ-ORACLE-008 (Fortune Roll with oracle follow-up), REQ-TENSION-002 (AI-suggested tension adjustment on scene completion), REQ-TENSION-004 (tension influence on interpretive oracle tone).

This adds: the challenge system, spotlight/pacing controls, prose expansion on beats, character voice notes and AI-suggested updates, email notifications, AI usage tracking, Fortune Roll follow-up with the interpretive oracle on exceptional results, AI-driven tension adjustment at scene boundaries, and tension-influenced oracle tone.

### Phase 3 - World Building and Narrative
REQ-NPC-001, REQ-NPC-002, REQ-WORLD-001 through REQ-WORLD-003, REQ-PROSE-002 through REQ-PROSE-004, REQ-ACT-002, REQ-ACT-003, REQ-SCENE-002, REQ-SCENE-003, REQ-S0-004, REQ-TENSION-005 (random events triggered by high tension).

This adds: NPC and world entry tracking with AI suggestions, relationship tracking, auto-narrative on completion, narrative export, AI nudges for scene/act completion, narrative voice configuration, and tension-driven random events at scene transitions and during play.

### Phase 4 - Future Considerations (Not in Scope)
- Public game discovery and listing.
- Full wiki system with cross-referenced pages and AI-generated summaries.
- Discord bot integration for notifications.
- Real-time/synchronous play mode with websockets.
- PDF/ePub export.
- Multiple simultaneous scenes within an act.
- Community-contributed word seed tables.
- Detailed contribution analytics.
