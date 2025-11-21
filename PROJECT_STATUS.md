# PROJECT STATUS

Only project manager keeps this file up-to-date. Remove outdated information and keep it actionable. Prune info from previous sprints after each new sprint.

## CURRENT STATUS

**Phase**: 2 - Story Skeleton
**Sprint**: 8 Complete - Bug Bash (PARTIAL)

### Progress Metrics

- **Quests**: 4/15
- **Tests**: 48/48 passing (+5 new tests)
- **Timelines**: 9 total
- **Integration**: 🟡 Partially fixed (critical bugs remain)

### Quest Integration Status

| Quest ID              | JSON | Timelines      | Trigger | Status                              |
| --------------------- | ---- | -------------- | ------- | ----------------------------------- |
| join_rebels           | ✅   | ✅ (3)         | ✅      | Working                             |
| rescue_prisoner       | ✅   | ✅ (2)         | ✅      | Immersion break (fallback choice)   |
| investigate_ruins     | ✅   | ✅ (2)         | ✅      | Working                             |
| secure_camp_defenses  | ✅   | ✅ (2)         | ✅      | Syntax bug in intro, fallback issue |
| battle_for_camp       | ❌   | ❌             | ❌      | Act 1 climax not started            |

### Known Issues (Next Sprint)

1. **Memory flag flow unclear** - Need ARCHITECT investigation (where/when flags set)
2. **Immersion-breaking fallbacks** - "Continue" choices need narrative replacements (WRITER)
3. **Syntax bug in secure_camp_defenses_intro.dtl** - Needs syntax fix (CODER)
4. **Task tool API errors** - Blocking agent spawning (MCP requires new session)

### Next Sprint Priority

1. Fix remaining Dialogic syntax bugs
2. ARCHITECT: Trace memory flag flow (use context7 MCP in fresh session)
3. WRITER: Replace generic fallback choices with narrative-appropriate desperate options
4. Full quest chain playthrough testing

## Last Sprint Post Mortem (Sprint 8 - 2025-11-21)

**Delivered**: Fixed Dialogic choice syntax (7 timelines), fixed has_memory_flag() bug, 5 new tests
**Failed**: Generic fallback choices break immersion, memory flag flow still unclear
**Root cause**: PM violated protocol (did investigation instead of delegating), Task tool API failures blocked ARCHITECT
**Waste**: ~40% (PM doing ARCHITECT work, CODER added bandaid vs proper fix)

**Key lesson**: When Task tool fails, escalate to user immediately instead of working around protocol

## Project Phases

Updates to project phases require user approval.

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

### Phase 3: Dialogue System (Month 4)

**Goal**: NPC conversations with conviction-gated options

**Deliverables**:

- [ ] Dialogic dialogue parser or custom system
- [ ] Dialogue UI (using Dialogic)
- [ ] 20-30 dialogue timelines
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
