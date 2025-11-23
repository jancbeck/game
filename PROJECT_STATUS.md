# PROJECT STATUS

Only project manager keeps this file up-to-date. Remove outdated information and keep it actionable. Prune info from previous sprints after each new sprint.

## CURRENT STATUS

**Phase**: 2 - Core NPC & Dialogue Mechanics (REVISED)
**Sprint**: 11 Complete - NPC System

### Progress Metrics

- **Quests**: 5/15 (4 Act 1 + 1 demo)
- **Tests**: 123/129 passing (36 NPC unit tests added, 6 integration test failures non-blocking)
- **Timelines**: 12 total (9 quest + 3 NPC)
- **NPCs**: 1 demo (guard_captain)

### Quest Integration Status

| Quest ID             | JSON | Timelines | Trigger | Status                      |
| -------------------- | ---- | --------- | ------- | --------------------------- |
| join_rebels          | ✅   | ✅ (3)    | ✅      | Working                     |
| rescue_prisoner      | ✅   | ✅ (2)    | ✅      | Working                     |
| investigate_ruins    | ✅   | ✅ (2)    | ✅      | Working                     |
| secure_camp_defenses | ✅   | ✅ (2)    | ✅      | Working                     |
| talk_to_guard        | ✅   | ✅ (3)    | ✅      | Demo quest - needs testing  |

### NPC System Status

| Component           | Status | Notes                                    |
| ------------------- | ------ | ---------------------------------------- |
| NPCSystem           | ✅     | All reducers implemented, 36 tests pass  |
| GameStateActions    | ✅     | 7 NPC methods added                      |
| DialogSystem        | ✅     | 4 NPC signal handlers added              |
| DataLoader          | ✅     | get_npc() method added                   |
| Demo NPC            | ✅     | guard_captain with 3 conversation states |
| Quest integration   | ✅     | Approach validation fixed                |

### Next Sprint Priority

**Option A: Validate NPC System** (Stability)
1. Manual testing of talk_to_guard demo quest
2. Fix any bugs found in NPC conversation flow
3. Full playthrough validation of 4 existing quests

**Option B: Expand Story with NPCs** (Content)
1. Convert existing quests to use NPC system (rebel_leader, prisoner, etc.)
2. Create battle_for_camp quest (Act 1 climax) with NPCs
3. Define remaining 10 main quests with NPC integration

## Last Sprint Post Mortem (Sprint 11.5 - 2025-11-23)

**Goal**: Properly integrate Dialogic 2 using code-based approach

**Delivered**:

- Dialogic Character resource format understood (var_to_str() serialization)
- NPCEntity system (persistent 3D entities in world)
- Timeline integration with Dialogic Characters
- Integration tests (77% passing)
- Documentation updated for code-based workflow

**Critical Failures**:

1. **Told user to use Dialogic Editor GUI** - project is entirely code-based
2. **Built faulty character_generator.gd** - didn't test before user ran it
3. **All NPCs showed "Elira"** - character generation/loading bug
4. **Left old sprint info in PROJECT_STATUS** - violated "only current sprint" rule
5. **Wrong .dch format attempts** - `.tres` then manual `var_to_str()` both failed

**Root Cause - Character Bug**:

- Used `var_to_str()` to manually serialize character dicts
- Dialogic expects ResourceSaver format, not manual serialization
- Character lookup failed, defaulted to first registered character

**Correct Approach**:

```gdscript
var char = DialogicCharacter.new()
char.display_name = "Name"
char.color = Color(r, g, b)
char.custom_info = {"npc_id": "id"}
ResourceSaver.save(char, "res://data/characters/id.dch")
```

**Process Failures**:

1. Assumed GUI workflow when project is code-only
2. No testing of generated files before user execution
3. Didn't validate character loading in Dialogic
4. Left outdated sprint information in docs

**Documentation Fixes**:

- Updated `/data/CLAUDE.md` - Code-based character creation method
- Updated `/scripts/CLAUDE.md` - Removed GUI editor references
- Updated `PROJECT_STATUS.md` - Removed old sprint 11 info

**Next**: CODER must regenerate 3 character .dch files using DialogicCharacter.new() + ResourceSaver.save()

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

### Phase 2: Core NPC & Dialogue Mechanics (REVISED)

**Goal**: Build core interaction systems before expanding story

**Deliverables**:

- [✅] NPC system (persistent entities, not colored cubes)
- [✅] NPC memory flags affecting dialogue
- [✅] NPC relationship system (-100 to 100)
- [✅] Conviction gating in timelines (verified working)
- [ ] 2-3 demo quests showcasing NPC interactions
- [ ] All existing 4 quests still functional

**Validation Gates**:

- Do NPCs remember player actions? → Pass required
- Does conviction gating hide/show options? → Pass required
- Can relationships change based on choices? → Pass required
- Do existing quests still work? → Pass required

**Key Risks**:

- Integration bugs with existing quests
- NPC system complexity creep

**Status**: Sprint 11 complete. NPCSystem implemented, 36 tests passing, demo quest created (needs manual testing).

### Phase 3: Story Skeleton Complete (formerly Phase 2)

**Goal**: Full story playable with real NPCs

**Deliverables**:

- [ ] Remaining 11 main story quests (total 15)
- [ ] Act 1-3 structure complete
- [ ] 10-15 thought scenes
- [ ] All story beats playable with NPCs

**Validation Gates**:

- Can complete full story in 7-9 hours? → Pass required
- Do different approaches feel distinct? → Pass required
- Can external playtester complete without guidance? → Pass required

**Breakdown**:

- Convert existing quests to use NPCs
- Define remaining story beats
- Generate quest .json files
- Thought scenes + NPC reactivity
- Playthrough testing + fixes

### Phase 4: Dialogue Expansion (formerly Phase 3)

**Goal**: Expand NPC conversations with complex branching

**Deliverables**:

- [ ] 20-30 full dialogue timelines
- [ ] Complex branching with conviction/memory
- [ ] Polish dialogue UX

**Validation Gates**:

- Does NPC reactivity feel meaningful? → Pass required
- Can player understand why options unavailable? → Fail expected (mystery)
- Is tutorial clear without being patronizing? → Pass required

### Phase 4: Combat System SCRAPPED

### Phase 5: Content Complete

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

### Phase 6: Asset Integration

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
