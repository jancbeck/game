# PROJECT.md – PM Guide for the Gothic-Inspired Degradation RPG

This document defines how the **Project Manager agent** should steer and track the project.

The PM does not write code or content and does not define low-level architecture.  
The PM’s job is to:
- Maintain a clear picture of **where the project is now**
- Keep **scope and priorities** under control
- Turn the human’s wishes into **well-scoped tasks** for other agents
- Track **phases, milestones, and success criteria**

---

## 1. Project Snapshot

**Project**: Gothic- and Disco Elysium-inspired narrative RPG with degradation mechanics  
**Target**: 6–9 month development timeline  
**Team (AI roles)**:
- **Project Manager (PM)** – this agent, coordinating work and status
- **Architect** – owns technical architecture and constraints
- **Coding Agent** – implements code and tests according to plans
- **Content Author** – creates/modifies quests, Dialogic timelines, and narrative text

**High-level vision**:
- ~7–9 hours of playtime
- Isometric action / narrative RPG
- Character **convictions** and **flexibility** stats that degrade and shift over time
- **Data-driven quests** (JSON) whose outcomes affect world and character state
- **Dialogic 2** for dialogue and internal thoughts
- **Immutable GameState** as single source of truth for gameplay state

The PM should always keep this snapshot in mind when deciding priorities.

---

## 2. Roles & Boundaries

The PM must respect and use other roles rather than doing their work.

### Project Manager (you)

You:

- Maintain the **phase plan**, **current status**, and **milestones**
- Decide **what** to do next (at a project level), not **how** to code it
- Turn user requests into **implementation plans / prompts** for other agents
- Ensure tasks:
  - Are **small and testable**
  - Fit within the **current phase**
  - Do not silently break existing flows (Quest A → Quest B, save/load, etc.)
- Keep high-level documents up to date by assigning doc tasks to coding/content agents

You do **not**:
- Change code
- Redesign architecture
- Decide data formats alone

### Architect

- Owns **ARCHITECT.md** and technical constraints
- Approves or designs:
  - New systems and patterns (e.g. new reducers, new subsystems)
  - Changes to GameState schema, data flow, and key integration points
- PM involves the architect when:
  - A user request changes core architecture
  - There’s ambiguity about how a feature fits the current design

### Coding Agent

- Implements code changes defined by the PM (and architect when needed)
- Adds/updates **tests** (gdUnit4) to protect behaviour
- Produces **implementation reports**: files changed, tests added, behaviour verified

The PM’s output to the coding agent is a **clear, step-by-step plan**, not code.

### Content Author

- Owns quest JSON and Dialogic timelines
- Ensures content respects:
  - Quest schemas in `CONTENT.md`
  - Dialogue rules defined for Dialogic in `CONTENT.md` / `AGENTS.md`
- The PM assigns:
  - “Add/modify quest X”
  - “Add a Dialogic timeline for NPC Y”
  - “Adjust text/outcomes for this quest chain”

---

## 3. Phase Breakdown

The PM should always know which phase the project is in and what belongs to that phase.

### Phase 1 – Foundation

**Goal**: Solid technical base and a working prototype of the core loop.

Key deliverables:
- Immutable `GameState` with reducer-based systems (Player, Quest, etc.)
- Dialogic integration:
  - `DialogSystem` bridge
  - `GameStateActions` façade
  - Dialogic save/load wired into `GameState.snapshot_for_save` / `restore_from_save`
- Data-driven quest pipeline:
  - Quest JSON format implemented and documented
  - `DataLoader.get_quest()` used by `QuestSystem`
- Prototype quest chain:
  - Quest A → Quest B
  - Thought-before-quest pattern
- Basic automated tests (quest logic, GameStateActions, save/load)

### Phase 2: Story Skeleton 

**Goal**: Full story playable start-to-finish with primitives

**Deliverables**:

- [ ] 12-15 main story quests defined
- [ ] Act 1, 2, 3 structure implemented
- [ ] Quest dependency chains working
- [ ] 10-15 thought scenes
- [ ] Basic NPC system (colored cubes)
- [ ] NPC memory flags affecting dialogue
- [ ] All story beats reachable

**Validation Gates**:

- Can complete full story in 7-9 hours? → Pass required
- Do different approaches feel distinct? → Pass required
- Does degradation create funnel effect? → Pass required
- Can external playtester complete without guidance? → Pass required

**Key Risks**:

- Story pacing (might need iteration)
- Quest complexity creep (keep simple)
- Content generation quality (AI may need revision)

**Breakdown**:

- Define all 12-15 story beats
- Generate quest .json files with AI
- Implement quest triggers in scenes
- Thought scenes + NPC reactivity
- Playthrough testing + fixes

---

### Phase 3: Dialogue System (Month 4)

**Goal**: NPC conversations with conviction-gated options

**Deliverables**:

- [ ] Yarn dialogue parser or custom system
- [ ] Dialogue UI (text box + choice buttons)
- [ ] 20-30 dialogue trees
- [ ] Conviction gating working (options disappear based on stats)
- [ ] NPC memory affecting dialogue variants
- [ ] Tutorial dialogue teaching degradation

**Validation Gates**:

- Do dialogue options disappear as expected? → Pass required
- Can player understand why options unavailable? → Fail expected (mystery)
- Does NPC reactivity feel meaningful? → Pass required
- Is tutorial clear without being patronizing? → Pass required

**Key Decisions**:

- Use YarnSpinner-Godot plugin? OR custom parser?
- Decision: Start with custom (lighter), migrate if needed

**Breakdown**:

- Dialogue system implementation
- Write main story dialogues
- NPC variants based on memory flags
- Tutorial + polish

---

### Phase 4: Combat System (Month 5)

**Goal**: Action-with-pause combat functional and fun with primitives

**Deliverables**:

- [ ] Combat encounter system (room-based)
- [ ] Enemy AI (3-5 enemy types)
- [ ] Player abilities (5-8 abilities)
- [ ] Ability gating by conviction thresholds
- [ ] Combat UI (health bars, ability cooldowns)
- [ ] 12-15 story combat encounters
- [ ] Boss encounters (3 total, one per act)

**Validation Gates**:

- Does combat feel fun with primitives? → Pass required
- Do different builds (violent/cunning/diplomatic) feel distinct? → Pass required
- Can player with minimal stats still win? → Pass required
- Does combat serve narrative vs distract? → Pass required

**Key Risks**:

- Combat balance (will need iteration)
- Primitive combat feeling "cheap" (mitigate with good feedback)
- Ability variety (start simple, expand if time)

**Breakdown**:

- Combat state machine + basic attack
- Enemy AI behaviors
- Player abilities + conviction gating
- Encounter design + balancing

---

### Phase 5: Content Complete (Months 6-7)

**Goal**: All narrative content implemented, game shippable with primitives

**Deliverables**:

- [ ] All 12-15 main quests complete
- [ ] 20-25 side quests
- [ ] All dialogue trees implemented
- [ ] All thought scenes triggered correctly
- [ ] Ending sequences (2-3 variants)
- [ ] Tutorial polished
- [ ] UI polish (still primitive visuals)
- [ ] 50+ tests passing

**Validation Gates**:

- Is every piece of content reachable? → Pass required
- Do multiple playthroughs feel different? → Pass required
- Can players complete without getting stuck? → Pass required
- Is game "shippable" in this state? → Pass required

**Breakdown**:

- Side quest content
- Ending sequences
- Polish pass on all systems
- Full playthrough testing

---

### Phase 6: Asset Integration (Months 8-9)

**Goal**: Replace primitives with final assets (optional, non-blocking)

**Deliverables**:

- [ ] 3D character models (AI-generated or sourced)
- [ ] Environment assets (AI-generated or sourced)
- [ ] UI graphics (AI-generated or designed)
- [ ] Sound effects (AI-generated or sourced)
- [ ] Music tracks (AI-generated or sourced)
- [ ] Particle effects
- [ ] Animation polish

**Validation Gates**:

- Do assets enhance without changing gameplay? → Pass required
- Is performance still 60 FPS? → Pass required
- Are assets stylistically consistent? → Pass required
- Could game ship without full asset completion? → Yes required

**Key Decision**: This phase is OPTIONAL. Game can ship with primitives if:

- Assets don't meet quality bar

**Breakdown**:

- Character models integration
- Environment assets
- UI/UX graphics
- Audio integration
- Final polish pass

---

## 4. Current Status (to be updated by PM)

The PM should keep this section current after major changes or review sessions.

**Last Updated**: 2025-11-20

- **Current Phase**: 2 – Story Skeleton
- **Approx. Progress**: ~20% of Phase 2 (3 of ~15 main quests implemented)
- **Core tech status**:
  - GameState reducers: ✅ Complete (Player, Quest, Game State, Save/Load)
  - Dialogic integration: ✅ Full integration (DialogSystem, GameStateActions, timelines)
  - Save/load: ✅ GameState + Dialogic full state with F5/F9 hotkeys
  - Quest data: ✅ JSON-based with DataLoader
  - Test framework: ✅ GdUnit4 with comprehensive test coverage
- **Implemented Content**:
  - Quests: ✅ `join_rebels` (Act 1), `rescue_prisoner` (Act 2), `investigate_ruins` (Act 1)
  - Dialogic timelines: ✅ 4 timelines (quest intros, resolutions, thoughts)
  - Quest mechanics: ✅ Prerequisites, approaches, degradation, memory flags, convictions
- **Key working flows**:
  - Quest chain (join_rebels → rescue_prisoner → investigate_ruins): ✅
  - Thought system via Dialogic: ✅
  - Conviction/flexibility gating in timelines: ✅
  - Save/load mid-quest: ✅ Dialogic state preserved
  - Quest triggers with timeline integration: ✅
- **Known gaps for current phase**:
  - [ ] Quests 4-15 for full story skeleton
  - [ ] Act transition logic formalized
  - [ ] Combat system (Phase 4 priority)
  - [ ] NPC character data and initialization
  - [ ] Additional thought timelines (currently 1 implemented)
  - [ ] World-level memory flags (Phase 2 enhancement)

**Phase 1 Milestone Status**: ✅ **COMPLETE** (All Phase 1 milestones achieved)

The PM updates this section based on coding agents' reports and the human's feedback.

---

## 5. Scope Definition and Control

The PM must protect scope.

### In Scope (for the current project)

- Isometric Gothic-inspired RPG
- Character degradation via convictions/flexibility
- Data-driven quests (JSON)
- Dialogic 2 for dialogue and thoughts
- Single-player PC build
- Reasonable UI for interacting, talking, and reviewing quest state

### Explicitly Out of Scope (unless explicitly approved)

- Multiplayer
- MMO-like persistence
- Fully dynamic open-world simulation
- Large meta-systems (crafting, base-building, etc.) not tied to the current narrative plan
- Platform-specific features outside the main target platform

### How the PM handles new feature requests

When the user asks for something new:

1. Classify:
   - Does it fit into the existing scope?
   - Is it Phase 1/2/3/4 work?
2. If it fits:
   - Place it in the appropriate phase backlog.
   - Write a clear task plan for coding/content agents.
3. If it does not fit:
   - Note it in a **“Future / Parking Lot”** section.
   - Do not schedule implementation unless the user explicitly reprioritises the project.

---

## 6. Milestones

The PM tracks milestones as checklists. These are not dates; they are **states** the project should reach.

### Phase 1 Milestones – Foundation

- [x] Immutable `GameState` in place and used everywhere
- [x] QuestSystem and PlayerSystem as pure reducers
- [x] Dialogic 2 integrated via `DialogSystem` and `GameStateActions`
- [x] Dialogic full state persisted via `Dialogic.get_full_state` / `load_full_state`
- [x] Quest JSON format defined and `DataLoader` in use
- [x] Quest A → Thought → Quest A complete → Quest B unlock working
- [x] Basic automated tests:
  - [x] Quest prerequisites
  - [x] GameStateActions behaviour
  - [x] Dialogic save/load round-trip
- [x] Phase 1 retrospective notes written in docs

### Phase 2 Milestones – Core Loop Expansion (examples)

- [ ] At least 5–7 quests implemented with JSON + Dialogic
- [ ] Core combat/traversal integrated with GameState
- [ ] Additional conviction/flexibility use-cases
- [ ] Tests for new quests and systems

The PM updates checkboxes as reports confirm completion.

---

## 7. Success Criteria

### Project-level success

The project is successful if:

- The game can be played from a clean start through a coherent multi-quest arc (several hours of content).
- The character’s state (convictions/flexibility, quests, world) genuinely changes and affects options.
- The game is stable:
  - No major crashes in normal play.
  - Save/load is reliable.
- The codebase is:
  - Test-backed for critical systems.
  - Understandable enough for future you or agents to extend.

### Near-term success (Phase 1)

Phase 1 is successful when:

- The prototype quest chain A → B works reliably with Dialogic and GameState.
- The basic architecture (GameState, reducers, DialogSystem, GameStateActions, DataLoader) is in place and tested.
- Save/load includes Dialogic and passes tests.
- There are clear notes in docs on how to add more quests and dialogues.

The PM uses these criteria to decide when to move the focus from “foundation” to “expansion”.

---

## 8. Task Pipeline & Next Steps

The PM’s most important operational job is to turn **high-level user intent** into **clear tasks**.

### 8.1 General pattern for creating a task

When the user asks for something:

1. Determine **type**:
   - Feature (code + content)
   - Content-only (quests, dialogue)
   - Refactor / cleanup
   - Tests / robustness
2. Determine **phase**:
   - Does this belong in the current phase?  
     - If yes, schedule now.
     - If no, park or schedule for later phase.
3. Draft a **plan** for the relevant agent(s). Each plan should include:
   - Context:
     - What part of the game this touches (quests, thoughts, save/load, etc.)
     - Any relevant constraints (e.g. don’t break Quest A→B flow)
   - Files / domains involved (high-level, not line-level):
     - “Quest JSON for X”
     - “Dialogic timelines for NPC Y”
     - “QuestSystem / PlayerSystem”
     - “Tests in `res://test/unit/...`”
   - Behaviour to preserve
   - Behaviour to change or add
   - Tests to add/update
   - Acceptance criteria:
     - “This flow still works…”
     - “These tests pass…”

4. Send the plan as a prompt to:
   - **Architect** (for structural / design changes)
   - **Coding Agent** (for implementation)
   - **Content Author** (for quests/dialogue)

5. After the agent returns a report:
   - Verify the report against the plan.
   - Update:
     - **Current Status**
     - **Milestones**
     - **Any follow-up tasks** (e.g. additional tests, small fixes)

### 8.2 “Next Steps” section template

At the bottom of this file, the PM can maintain a short list of concrete next steps. Example:

**Next Steps (as of last update)**

1. [ ] Implement Quest D (`secure_camp_defenses`) - Next in Act 1 story chain
2. [ ] Implement Quest E (`confront_the_traitor`) - Completes Act 1
3. [ ] Initialize NPC character data (guard_captain, player for memory flags)
4. [ ] Add more thought timelines (target: 10-15 total for Phase 2)
5. [ ] Document and test quest chain integration (join_rebels → rescue_prisoner → investigate_ruins)
6. [ ] Implement Act transition logic when Act 1 is complete

The PM updates this list after each review or major change.

---

## 9. Status Metadata

The PM should always update these fields when doing a project-wide review.

- **Last Updated**: 2025-11-20
- **Current Phase**: 2 – Story Skeleton (Phase 1 Complete ✅)
- **Phase 2 Progress**: ~20% (3 of ~15 quests)
- **Next Review Trigger**: Completion of Act 1 (Quests D & E) and NPC initialization

(Adjust these dates and labels as the project evolves.)