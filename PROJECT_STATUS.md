# PROJECT STATUS

Only project manager keeps this file up-to-date. Remove outdated information and keep it actionable. Prune info from previous sprints.

## CURRENT STATUS

**Phase**: 2 - Story Skeleton
**Sprint**: Completed - Resolution Timeline Feature

### Progress Metrics

- **Quests**: 5/15 (Act 1: 4 main + 1 thought)
- **Tests**: 43/43 passing
- **Quest chain**: 4 connected quests functional
- **Story arc**: Act 1 progression through secure_camp_defenses

### Test Room Layout

- (-5, 0, -5): secure_camp_defenses (locked until investigate_ruins done)
- (0, 0, -5): join_rebels (thought timeline)
- (5, 0, -5): rescue_prisoner (intro timeline)
- (10, 0, -5): investigate_ruins (intro when available, resolution when active)

### Known Issues

**Architecture & Tests**: NONE blocking

**Content Gaps**:
- secure_camp_defenses: missing intro/resolution timelines
- rescue_prisoner: missing resolution timeline
- join_rebels: has thought timeline but no intro/resolution quests
- report_to_rebel_leader: ORPHANED (empty outcomes, no follow-up)

**Integration Issues**:
- secure_camp_defenses trigger in test_room has empty timeline_id
- No Act 2 content structure started (0/5 quests)
- No Act 3 content structure started (0/4 quests)

### Next Sprint Priority

**Phase 2 Completion Blocker**: Need 10 more quests + 10-15 thought timelines

**Recommended Next Sprint**:
1. **WRITER**: Fill critical timeline gaps (join_rebels intro, rescue_prisoner resolution, secure_camp_defenses intro/resolution)
2. **WRITER**: Fix orphaned quest (give report_to_rebel_leader outcomes or remove)
3. **WRITER**: Create Act 1 climax quest (battle_for_camp) with full JSON + timelines
4. **CODER**: Update test_room trigger for secure_camp_defenses with timeline_id
5. **ARCHITECT**: Add end-to-end quest chain integration tests

**Alternative Options**:
- **Option A** (Conservative): Content pass first - complete all missing timelines, then new quests
- **Option B** (Aggressive): New quests first - create Act 1 climax + Act 2 foundation
- **Option C** (Balanced): Parallel - WRITER creates new quests while CODER fixes integration gaps

### Deliverables Completed

**Technical**:

- ✅ 43/43 tests passing (was 37, added 6 new tests)
- ✅ secure_camp_defenses quest created & integrated
- ✅ Memory flag system bug fixed (global → world.memory_flags)
- ✅ Context-aware timeline selection (intro vs resolution)
- ✅ All 4 quest triggers functional in test_room

**Content**:

- ✅ Quest chain: join_rebels → rescue_prisoner → investigate_ruins → secure_camp_defenses
- ✅ Dual-purpose triggers (intro when available, resolution when active)
- ✅ Locked quest feedback (RED on-screen message)

**Bugs Fixed**:

- CRITICAL: Dialogic regression (@export removal broke scene data)
- Prerequisite bypass (investigate_ruins accessible without rescue_prisoner)
- Triggers disappearing when quest became active (not just completed)
- No user feedback for locked quests (console-only)

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
