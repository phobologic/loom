# Loom Development Plan - Phase 3: World Building and Narrative

## Approach

Phase 3 adds the world-building tools (NPCs, world entries, relationships), the narrative pipeline (voice configuration, scene/act compilation, export), AI nudges for scene/act completion, and the random events system driven by high tension.

Scene and act completion mechanics were pulled into Phase 2 (Step 26). What remains here is the AI nudge layer that suggests when completion might be appropriate.

Narrative voice configuration comes before narrative compilation because compilation uses it. Scene compilation comes before act compilation because act narratives build from scene narratives. NPC and world entry tracking are mostly independent but both feed into relationship tracking.

This phase also picks up two requirements that fell through the cracks in Phases 1 and 2.

### Cross-Cutting Concerns

**REQ-TECH-002 (API Design):** All data-mutating operations should be available as API endpoints (JSON in/out) alongside server-rendered views. This is an architectural convention to follow throughout all phases, not a discrete step. FastAPI auto-generates OpenAPI docs. Server-rendered pages and API endpoints should call the same underlying logic.

---

## Steps

### Step 40: Game Organizer Admin Features

The full organizer role beyond role assignment (which was covered in Phase 1 Step 4). The organizer can remove a player from the game, pause a game, resume a paused game, and archive a game (making it read-only but still viewable). All organizer actions are visible to all players. The organizer has no special narrative authority.

**Requirements:** REQ-GAME-003 (complete), REQ-GAME-005 (pause/archive states)

---

### Step 41: NPC Creation and Tracking

Any player can manually create an NPC entry (name, description, notes). NPC entries are shared and visible to all players. Any player can edit any NPC entry. NPCs are accessible from the game dashboard and can be referenced from scenes.

**Requirements:** REQ-NPC-001

---

### Step 42: AI-Suggested NPC Entries

The AI monitors beats for references to new named characters who aren't existing PCs or NPCs. When detected, the AI suggests creating an NPC entry with a proposed name, description, and notes based on their appearances in the fiction. Any player can approve, modify, or dismiss the suggestion.

**Requirements:** REQ-NPC-002

---

### Step 43: World Entry Tracking

Any player can create a world entry with a name, type (location, faction, item, concept, other), and description. World entries are shared and visible to all players. Any player can edit any world entry. Accessible from the game dashboard.

**Requirements:** REQ-WORLD-001

---

### Step 44: AI-Suggested World Entries

The AI monitors beats for references to new locations, organizations, or significant items that don't have existing entries. Suggests creating entries with proposed details based on context. Any player can approve, modify, or dismiss.

**Requirements:** REQ-WORLD-002

---

### Step 45: Relationship Tracking

Relationships can be created manually by any player between any combination of characters, NPCs, and world entries (e.g., "Kira - rivals with - Dock Master Venn"). The AI can suggest relationships based on fictional events. Relationships are visible on the relevant entity pages.

**Requirements:** REQ-WORLD-003

---

### Step 46: Narrative Voice Configuration

During Session 0, the AI offers sample narrative voice options based on the chosen genre/tone (e.g., terse noir, lyrical fantasy, dry humor). The group selects or customizes a default voice. Stored as part of game configuration and used for all prose expansion and narrative compilation. This extends the Session 0 flow built in Phase 1.

**Requirements:** REQ-S0-004

---

### Step 47: Scene Narrative Compilation

When a scene is completed (and auto-narrative is enabled in game settings), the AI generates a prose narrative for the scene. Based on all narrative and roll events within the scene's beats, using the game's narrative voice and character voice notes. OOC events excluded. Stored with the scene and viewable by all players. Read-only in v1.

**Requirements:** REQ-PROSE-002

---

### Step 48: Act Narrative Compilation

When an act is completed (and auto-narrative is enabled), the AI generates a prose narrative for the act, incorporating scene narratives and the act's overall arc. Uses the act's guiding question and resolution as framing. Stored with the act and viewable by all players. Read-only in v1.

**Requirements:** REQ-PROSE-003

---

### Step 49: Narrative Export

Players can export narratives in markdown format. Options: individual scene narratives, individual act narratives, or a combined export of all completed act narratives in sequence. Export includes act and scene titles and guiding questions as structural headers.

**Requirements:** REQ-PROSE-004

---

### Step 50: AI Nudge for Scene Completion

The AI monitors the fiction for signals that the current scene's guiding question has been resolved. When detected, a non-blocking suggestion is surfaced to all players. Players can dismiss it or initiate the completion proposal. The AI does not auto-complete scenes.

**Requirements:** REQ-SCENE-003

---

### Step 51: AI Nudge for Act Completion

Same pattern as scene completion nudges but for acts. The AI monitors for signals that the act's guiding question has been answered and suggests the group consider completing the act.

**Requirements:** REQ-ACT-003

---

### Step 52: Random Events Triggered by High Tension

Two triggers for random events:

**At scene start:** Loom rolls to determine if the scene is altered or interrupted based on the current tension. Higher tension means higher probability of disruption. An "altered" scene gets a suggested modification (something is different from what the players expected). An "interrupted" scene gets an entirely different scene suggestion using a word seed pair for inspiration. The group can accept (replacing their proposed scene), weave it in (modifying their scene to include the interruption), or reject it (proceeding as planned, but the rejected event is noted as a potential future thread).

**During play:** When a Fortune Roll rolls doubles and the individual digit is equal to or less than the current tension, a random event fires alongside the Fortune Roll result. The AI generates a brief complication or twist using a word seed pair and the current context.

All random events are presented as suggestions to the group, not forced into the fiction. They follow the standard beat proposal and approval flow. At low tension (1-3), random events are very rare. At high tension (7-9), they are frequent and disruptive.

**Requirements:** REQ-TENSION-005

---

## Requirements Coverage Check

All requirements from the Loom Requirements Document are covered across the three phase plans:

- **Phase 1 (Steps 1-25):** REQ-TECH-001, REQ-TECH-003, REQ-TECH-004, REQ-AUTH-001, REQ-AUTH-002, REQ-GAME-001, REQ-GAME-002, REQ-GAME-003 (partial), REQ-GAME-004, REQ-GAME-005, REQ-S0-001, REQ-S0-002, REQ-S0-003, REQ-S0-005, REQ-S0-006, REQ-CHAR-001, REQ-ACT-001, REQ-SCENE-001, REQ-SCENE-004, REQ-BEAT-001, REQ-BEAT-002, REQ-BEAT-003, REQ-BEAT-004, REQ-BEAT-006, REQ-DICE-001, REQ-DICE-002, REQ-ORACLE-001, REQ-ORACLE-002, REQ-ORACLE-003, REQ-ORACLE-004, REQ-ORACLE-005, REQ-ORACLE-006, REQ-ORACLE-007, REQ-TENSION-001, REQ-TENSION-003, REQ-VOTE-001, REQ-VOTE-002, REQ-NOTIFY-001, REQ-AI-001, REQ-AI-003, REQ-AI-004
- **Phase 2 (Steps 26-39):** REQ-SCENE-002, REQ-ACT-002, REQ-TENSION-002, REQ-TENSION-004, REQ-CHALLENGE-001, REQ-CHALLENGE-002, REQ-PACE-001, REQ-PACE-002, REQ-PACE-003, REQ-CHAR-002, REQ-CHAR-003, REQ-PROSE-001, REQ-BEAT-005, REQ-ORACLE-008, REQ-AI-002, REQ-NOTIFY-002
- **Phase 3 (Steps 40-52):** REQ-GAME-003 (complete), REQ-NPC-001, REQ-NPC-002, REQ-WORLD-001, REQ-WORLD-002, REQ-WORLD-003, REQ-S0-004, REQ-PROSE-002, REQ-PROSE-003, REQ-PROSE-004, REQ-SCENE-003, REQ-ACT-003, REQ-TENSION-005
- **Cross-cutting:** REQ-TECH-002
