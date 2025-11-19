# Project Plan: Gothic-Inspired Degradation RPG

**Target**: 6-9 month development timeline
**Team**: Solo developer + AI coding agents
**Scope**: 7-9 hour narrative RPG with degradation mechanics
**Budget**: Minimal (AI-generated assets, free tools)

---

## I. Current Status

**Phase**: 1 (Foundation)
**Progress**: 85% complete
**Hours Invested**: ~28 hours
**Tests Passing**: 26/26

### Completed

- ✅ Core systems (GameState, PlayerSystem, QuestSystem, ThoughtSystem)
- ✅ Data pipeline (DataLoader, YAML/JSON parsing)
- ✅ Quest chain with prerequisites
- ✅ Save/load system
- ✅ Visual degradation (color shifting)
- ✅ Debug UI
- ✅ Internal monologue system
- ✅ 26 unit/integration tests passing

### In Progress

- ⏳ Approach selection UI (currently auto-complete)
- ⏳ Second thought scene (only one example exists)

### Blocked

- None currently

---

## II. Phase Breakdown

### Phase 1: Foundation (Months 1-2)

**Goal**: Prove architecture works end-to-end with playable prototype

**Deliverables**:

- [x] Immutable state architecture validated
- [x] Quest system with approach-based resolution
- [x] Save/load preserving exact state
- [x] Internal monologue system
- [x] Debug UI showing stats
- [x] Visual degradation feedback (color change)
- [ ] Approach selection UI (instead of auto-complete)
- [ ] 3-5 complete quests with thought scenes
- [ ] 35+ tests passing

**Validation Gates**:

- Can complete 3-quest chain with different approaches? → Pass required
- Do stats degrade visibly? → Pass required
- Does save/load restore exact gameplay? → Pass required
- Can AI agents generate new quests from templates? → Pass required

**Estimated Hours**: 30-35 total
**Current Hours**: 28
**Remaining**: 2-7 hours

**Next Session Tasks**:

1. Add approach selection UI (2 hours)
2. Create 2-3 more thought scenes (1 hour)
3. Add 2-3 more quests (2 hours)
4. Polish pass (1 hour)

---

### Phase 2: Story Skeleton (Month 3)

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

**Estimated Hours**: 20-30 hours
**Key Risks**:

- Story pacing (might need iteration)
- Quest complexity creep (keep simple)
- Content generation quality (AI may need revision)

**Breakdown**:

- Week 1: Define all 12-15 story beats (4 hours)
- Week 2: Generate quest .md files with AI (8 hours)
- Week 3: Implement quest triggers in scenes (6 hours)
- Week 4: Thought scenes + NPC reactivity (8 hours)
- Week 5: Playthrough testing + fixes (4 hours)

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

**Estimated Hours**: 15-20 hours

**Key Decisions**:

- Use YarnSpinner-Godot plugin? OR custom parser?
- Decision: Start with custom (lighter), migrate if needed

**Breakdown**:

- Week 1: Dialogue system implementation (6 hours)
- Week 2: Write main story dialogues (6 hours)
- Week 3: NPC variants based on memory flags (4 hours)
- Week 4: Tutorial + polish (4 hours)

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

**Estimated Hours**: 25-35 hours

**Key Risks**:

- Combat balance (will need iteration)
- Primitive combat feeling "cheap" (mitigate with good feedback)
- Ability variety (start simple, expand if time)

**Breakdown**:

- Week 1: Combat state machine + basic attack (8 hours)
- Week 2: Enemy AI behaviors (8 hours)
- Week 3: Player abilities + conviction gating (10 hours)
- Week 4: Encounter design + balancing (8 hours)

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

**Estimated Hours**: 30-40 hours

**Breakdown**:

- Weeks 1-2: Side quest content (12 hours)
- Weeks 3-4: Ending sequences (8 hours)
- Weeks 5-6: Polish pass on all systems (12 hours)
- Weeks 7-8: Full playthrough testing (8 hours)

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

**Estimated Hours**: 40-60 hours

**Key Decision**: This phase is OPTIONAL. Game can ship with primitives if:

- Budget constraints
- Timeline pressure
- Assets don't meet quality bar

**Breakdown**:

- Weeks 1-2: Character models integration (12 hours)
- Weeks 3-4: Environment assets (15 hours)
- Weeks 5-6: UI/UX graphics (10 hours)
- Weeks 7-8: Audio integration (8 hours)
- Week 9: Final polish pass (5 hours)

---

## III. Hour Breakdown by Category

### Development Time Allocation

**Core Systems** (Phase 1): 30-35 hours

- State management: 8 hours
- Quest system: 10 hours
- Thought system: 5 hours
- Save/load: 3 hours
- Testing: 4-9 hours

**Story Content** (Phase 2): 20-30 hours

- Story design: 4 hours
- Quest generation: 8 hours
- Scene setup: 6 hours
- NPC implementation: 4 hours
- Thought scenes: 4 hours
- Testing: 4 hours

**Dialogue** (Phase 3): 15-20 hours

- System implementation: 6 hours
- Content writing: 6 hours
- NPC variants: 4 hours
- Testing: 3 hours

**Combat** (Phase 4): 25-35 hours

- Core mechanics: 16 hours
- Abilities: 10 hours
- Balance: 8 hours
- Testing: 1 hour

**Content Complete** (Phase 5): 30-40 hours

- Side quests: 12 hours
- Endings: 8 hours
- Polish: 12 hours
- Testing: 8 hours

**Assets** (Phase 6): 40-60 hours (OPTIONAL)

- Models: 12 hours
- Environments: 15 hours
- UI: 10 hours
- Audio: 8 hours
- Polish: 5-15 hours

**Total (without assets)**: 120-160 hours
**Total (with assets)**: 160-220 hours

---

## IV. Timeline Scenarios

### Scenario A: 5 hours/week

- Phase 1 complete: Week 7 (current: Week 6)
- Phase 2 complete: Week 13
- Phase 3 complete: Week 17
- Phase 4 complete: Week 24
- Phase 5 complete: Week 32
- **Total: 8 months to content complete**
- Phase 6 (optional): +3 months

**Result**: 8-11 months total (within 6-9 month goal if skip assets)

---

### Scenario B: 10 hours/week

- Phase 1 complete: Week 4 (current: Week 3)
- Phase 2 complete: Week 7
- Phase 3 complete: Week 9
- Phase 4 complete: Week 13
- Phase 5 complete: Week 17
- **Total: 4 months to content complete**
- Phase 6 (optional): +6 weeks

**Result**: 4-6 months total (ahead of schedule)

---

### Scenario C: Variable (realistic for hobby project)

- Some weeks: 10 hours (motivated)
- Some weeks: 2 hours (busy)
- Average: 6 hours/week

**Result**: 6-8 months to content complete (on track)

---

## V. Scope Control

### Core Scope (MUST HAVE)

**Story**:

- 12-15 main quests
- 3 acts with clear structure
- Degradation mechanic fully implemented
- 2-3 ending variants

**Mechanics**:

- Quest system with approaches
- Internal monologue system
- Conviction gating
- Basic combat
- Save/load

**Content**:

- 30,000 words dialogue/narrative
- 10-15 thought scenes
- 12-15 combat encounters

**Technical**:

- 60 FPS with primitives
- Zero crashes in full playthrough
- All tests passing

---

### Extended Scope (NICE TO HAVE)

**If time permits**:

- 20-25 side quests
- More NPC reactivity variants
- Additional combat abilities
- More thought scenes
- Richer endings

**Only add if**:

- Core scope complete
- Tests still passing
- Schedule permits

---

### Out of Scope (EXPLICITLY EXCLUDED)

**Will NOT include**:

- Multiplayer
- Procedural generation
- Crafting system
- Complex skill trees
- Romance options
- Open world exploration
- Voice acting
- Complex animation systems
- New game plus

**Rationale**: These don't serve core degradation mechanic and would 3x development time.

---

## VI. Risk Management

### High-Risk Items

**Risk 1: AI-generated content quality**

- **Impact**: High (affects entire game)
- **Probability**: Medium
- **Mitigation**:
  - Review all AI content before integration
  - Have templates/examples for AI to follow
  - Budget time for rewrites
- **Contingency**: Write content manually if AI quality insufficient

**Risk 2: Combat balance**

- **Impact**: Medium (can frustrate players)
- **Probability**: High (always hard to balance)
- **Mitigation**:
  - Playtesting early and often
  - Adjustable difficulty via data files
  - "Desperate" options ensure progress
- **Contingency**: Ship with easier balance, patch later

**Risk 3: Scope creep**

- **Impact**: Critical (could derail timeline)
- **Probability**: Medium
- **Mitigation**:
  - This document defines scope
  - Review weekly: "Does this serve degradation mechanic?"
  - AI agents can't add features without approval
- **Contingency**: Cut extended scope, ship core only

**Risk 4: Asset pipeline delays**

- **Impact**: Low (primitives work)
- **Probability**: High (assets always take longer)
- **Mitigation**:
  - Placeholder-first development
  - Assets are Phase 6 (can skip)
- **Contingency**: Ship with primitives

---

### Medium-Risk Items

**Risk 5: AI agent code quality drift**

- **Impact**: Medium (technical debt)
- **Probability**: Medium
- **Mitigation**:
  - AGENTS.md as source of truth
  - Require tests for all code
  - Human review before merge
- **Contingency**: Refactor sessions every 2 weeks

**Risk 6: Mystery too opaque**

- **Impact**: Medium (player confusion)
- **Probability**: Medium
- **Mitigation**:
  - Playtesting with fresh users
  - Tutorial teaches mechanic
  - Debug UI available as fallback
- **Contingency**: Add optional transparency toggle

---

## VII. Success Criteria

### Phase 1 Success

- [x] 26+ tests passing
- [ ] 3-quest chain completable
- [ ] Stats visibly degrade
- [ ] Save/load works flawlessly
- [ ] Approach selection UI functional

**Current**: 4/5 complete (90%)

---

### Phase 2 Success

- [ ] Full story playable start-to-finish
- [ ] 7-9 hour playtime achieved
- [ ] External playtester completes without help
- [ ] All story beats reachable

---

### Phase 3 Success

- [ ] Dialogue options gate based on convictions
- [ ] NPC reactivity visible to player
- [ ] Tutorial clear and effective
- [ ] 20+ dialogue trees implemented

---

### Phase 4 Success

- [ ] Combat fun with primitives
- [ ] Different builds feel distinct
- [ ] Player with min stats can still win
- [ ] Combat doesn't overshadow narrative

---

### Phase 5 Success

- [ ] All content implemented
- [ ] Multiple playthroughs feel different
- [ ] Zero softlocks possible
- [ ] Game shippable in current state

---

### Phase 6 Success (OPTIONAL)

- [ ] Assets enhance experience
- [ ] 60 FPS maintained
- [ ] Visual consistency achieved
- [ ] Could still ship without some assets

---

## VIII. Weekly Workflow

### Standard Week Pattern

**Monday** (Planning - 1 hour):

- Review previous week's progress
- Define this week's deliverables
- Write AI agent prompts
- Update PROJECT.md status

**Tuesday-Thursday** (Development - 1-3 hours/day):

- AI agents generate code
- Review and integrate
- Run tests
- Playtest changes

**Friday** (Validation - 1 hour):

- Full test suite run
- Playthrough of new content
- Document any issues
- Plan next week

**Weekend** (Optional - 2-4 hours):

- Content writing
- Design work
- Learning/research
- Asset sourcing

---

### Monthly Review

**Last week of each month**:

1. Review phase completion percentage
2. Update timeline if needed
3. Adjust scope if behind schedule
4. Validate architecture still working
5. Update all documentation

---

## IX. Budget

### Development Costs

**Tools** (all free):

- Godot 4.5: $0
- GDScript Toolkit: $0
- gdUnit4: $0
- Git: $0
- AI coding agents: $0 (assuming using free tier)

**Assets** (if Phase 6):

- AI-generated models: $0-50 (API costs)
- AI-generated textures: $0-50
- AI-generated audio: $0-50
- Font licenses: $0-20
- **Total: $0-170**

**Marketing** (out of scope):

- TBD if project successful

**Total Development Budget: $0-170**

---

## X. Milestones & Checkpoints

### Major Milestones

**Milestone 1: Walking Skeleton** (Current)

- Date: Week 6
- Deliverable: Core architecture proven
- Status: 90% complete

**Milestone 2: Story Skeleton**

- Date: Week 12-13
- Deliverable: Full story playable with primitives
- Status: Not started

**Milestone 3: Feature Complete**

- Date: Week 24
- Deliverable: All gameplay systems implemented
- Status: Not started

**Milestone 4: Content Complete**

- Date: Week 32
- Deliverable: All narrative content implemented
- Status: Not started

**Milestone 5: Ship-Ready**

- Date: Week 36-40
- Deliverable: Game polished and releasable
- Status: Not started

---

### Decision Points

**Decision Point 1: After Phase 2**

- Question: Is story compelling enough to continue?
- Criteria: External playtester engagement
- Options:
  - A) Continue to Phase 3 (if compelling)
  - B) Iterate on story (if not compelling)
  - C) Cancel project (if fundamentally flawed)

**Decision Point 2: After Phase 5**

- Question: Ship with primitives or add assets?
- Criteria: Time remaining, budget, gameplay quality
- Options:
  - A) Ship with primitives (if time/budget tight)
  - B) Proceed to Phase 6 (if resources available)
  - C) Hybrid approach (key assets only)

---

## XI. Current Next Steps

### Immediate (This Week)

1. **Approach Selection UI** (2 hours)

   - Replace auto-complete with button selection
   - Show approach requirements
   - Grey out unavailable approaches
   - Test with existing quests

2. **Additional Thought Scenes** (1 hour)

   - Create 2-3 more thought .json files
   - Wire to quest completion triggers
   - Test conviction accumulation

3. **Additional Quests** (2 hours)
   - Write 2-3 more quest .md files
   - Test quest chain dependencies
   - Verify data pipeline scales

**Total: 5 hours to Phase 1 complete**

---

### Next Week (Phase 2 Start)

1. **Story Beat Outline** (4 hours)

   - Define all 12-15 main quests
   - Map Act structure
   - Identify key choice moments
   - Document in design doc

2. **NPC System** (3 hours)

   - Create NPC colored cubes
   - Basic interaction system
   - Memory flag storage
   - Test NPC spawning

3. **Quest Generation** (3 hours)
   - Generate 3-5 quests with AI
   - Review and edit
   - Integrate into game
   - Test full chains

**Total: 10 hours for Phase 2 start**

---

## XII. Communication

### Status Updates

**Weekly**: Update this document's "Current Status" section
**Monthly**: Full phase review and timeline adjustment
**Milestones**: Detailed writeup of what was learned

### Documentation Maintenance

**AGENTS.md**: Update after any architectural change
**ARCHITECTURE.md**: Update if design rationale changes
**PROJECT.md**: Update weekly with progress
**CONTENT_SPEC.md**: Update if data formats change

---

**Last Updated**: November 19, 2025
**Next Review**: After Phase 1 completion (~Week 7)
**Current Phase**: 1 (Foundation) - 90% complete
