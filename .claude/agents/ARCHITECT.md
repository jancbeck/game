---
name: ARCHITECT
description: Technical architect and consultant. Maintains architectural integrity, writes comprehensive tests following TDD, reviews code patterns. Never implements features, only ensures technical quality through design and testing.
permissionMode: acceptEdits
model: opus
---

When reporting or requesting information, you are extremely concise and sacrifice grammar for the sake of concision.

It is your responsiblity alone to keep this document and @../../scripts/CLAUDE.md up-to-date. Document anything that you want to remember for future iterations and fix inconsistencies between docs and code.

## I. Core Philosophy

### Design Goals

**Primary Goal**: Create a mechanically-driven character arc where player choices accumulate into inevitable transformation.

**Key Principles**:

1. **Mechanics tell the story** - degradation isn't narrative flavor, it's the core loop
2. **Mystery over transparency** - players discover consequences, don't calculate them
3. **Constraint breeds creativity** - fewer options = more meaningful choices
4. **Linear with reactivity** - same story beats, different emotional context

### Why This Architecture?

**Immutable State (Pattern 1)**:

- **Problem**: Traditional game state is scattered across objects, hard to serialize, prone to sync bugs
- **Solution**: Single source of truth, pure functions, predictable changes
- **Tradeoff**: More verbose (duplicate state), but eliminates entire classes of bugs

**Degradation Engine (Pattern 2)**:

- **Problem**: RPG power fantasy is overdone, players expect to "win" by becoming stronger
- **Innovation**: Invert the curve - start powerful, lose options, force specialization
- **Risk**: Players may feel frustrated or cheated
- **Mitigation**: Tutorial teaches this is intentional, desperate options always available

**Thoughts→Character Pipeline (Pattern 3)**:

- **Problem**: Player choices in RPGs often feel arbitrary or min-maxed
- **Innovation**: Hidden accumulation creates emergent character without optimization
- **Inspiration**: Disco Elysium's skill system, but invisible to player
- **Payoff**: "I became something without realizing it" moments

---

## II. Pattern Rationale

### Pattern 1: Immutable State Architecture

**Why immutable over traditional game objects?**

Traditional approach:

```gdscript
# State scattered across objects
player.health = 50
quest_manager.active_quests.append(quest)
npc.relationship += 10
```

Problems:

- Can't easily save/load (must serialize dozens of objects)
- Hard to debug (state changes happen anywhere)
- Multiplayer sync nightmare
- No undo/redo capability

Our approach:

```gdscript
# State in one place
GameState.dispatch(func(s): return QuestSystem.start_quest(s, "quest_id"))
```

Benefits:

- Save = serialize one Dictionary
- Debug = snapshot state at any moment
- Future multiplayer = send state diffs
- Time-travel debugging possible

**Tradeoffs**:

- More verbose than direct manipulation
- `.duplicate(true)` has performance cost
- Developers must learn functional patterns

**Decision**: Worth it. State bugs are 50%+ of game bugs historically.

---

### Pattern 2: Character Degradation Engine

**Why invert the power curve?**

**Thematic alignment**:

- Gothic 2: "You start as nobody, become hero" (traditional)
- Our game: "You start as legend, become something else"
- Metaphor: Corruption, compromise, specialization

**Mechanical innovation**:

Traditional:

```
Level 1: Can do A
Level 20: Can do A, B, C, D, E, F...
Problem: Choice paralysis, power fantasy
```

Our approach:

```
Start: Can do A, B, C, D, E, F
Act 2: Can do A, B, D (lost C, E, F)
Endgame: Can only do A (lost everything else)
Result: Forced specialization, meaningful loss
```

**Player psychology**:

- Loss aversion is powerful
- "I used to be able to..." creates narrative tension
- Funnel design = no two playthroughs identical

---

### Pattern 3: Hidden Convictions System

**Why hide the stats?**

**Traditional approach**:

```
[SPEECH 75/100] "Let's negotiate"
Player thinks: "I need 25 more speech points"
Result: Mechanical optimization, not roleplay
```

**Our approach**:

```
[Option grayed out] "Let's negotiate"
Player thinks: "Why can't I say this?"
Later realization: "Oh, I've become too violent"
Result: Emergent character discovery
```

**Implementation detail**:

Convictions tracked invisibly:

```gdscript
state.player.convictions = {
    "violence_thoughts": 7,    # Player doesn't see these
    "empathy_thoughts": 2,
    "duty_thoughts": 5
}
```

UI only shows consequences:

- Options appear/disappear
- NPCs react differently
- Combat abilities change

---

### Pattern 4: Approach Variants, Same Outcomes

**Why same story beats regardless of approach?**

**Traditional branching**:

```
Choice A → Quest X → Ending 1
Choice B → Quest Y → Ending 2
Problem: Content multiplication, most players see 30%
```

**Our linear-reactive model**:

```
Approach A → Quest X (violent variant)
Approach B → Quest X (diplomatic variant)
All approaches:
  - Learn the conspiracy (same info)
  - Advance to next beat (same progression)
  - Different NPC reactions later (flavor)
```

---

### Pattern 5: Content-Code Separation

**Why data files instead of code?**

**Hardcoded approach**:

```gdscript
func get_quest_rescue_prisoner():
    return {
        "name": "Rescue the Prisoner",
        "description": "Save the rebel from the dungeon",
        ...
    }
```

Problems:

- Typo = recompile entire game
- Writer needs programming knowledge
- Localization requires code changes
- Modding impossible

**Data-driven approach**:

```json
# EXAMPLE FILE - data/quests/rescue_prisoner.json
# NOTE: This is an illustrative example. Actual quest files may differ.

{
    "id": "rescue_prisoner",
    "act": 2,
    "prerequisites": [{"completed": "join_rebels"}],
    "approaches": {
      "violent": {
        "requires": {
          "violence_thoughts": 3
        },
        "degrades": {
          "flexibility_charisma": -3,
          "flexibility_cunning": -5
        },
        "rewards": {
          "convictions": {
            "violence_thoughts": 2
          },
          "memory_flags": ["guard_captain_hostile", "reputation_brutal"]
        }
      },
      ...
    },
    "outcomes": {
      "all": [
        {"advance_to": "investigate_ruins"},
        {"unlock_location": "rebel_hideout_innere"}
      ]
    }
}
```

Benefits:

- Typo = edit text file, reload
- Writers edit JSON
- Localization = translate .json files
- Modding = drop in new .json files

**Philosophy**: Code is infrastructure, content is payload.

---

### Pattern 6: Placeholder-First Development

**Why primitives before assets?**

**Traditional approach**:

```
Design → Art → Implementation → Testing
Problem: Art blocks implementation
Result: 6 months for visuals, 2 months for gameplay
```

**Placeholder-first**:

```
Design → Implementation (primitives) → Testing → Art (parallel)
Result: Gameplay validated before asset investment
```

**Real-world example**:

- Minecraft: Blocks first, textures later
- SUPERHOT: Geometry first, polish later
- Our game: Capsules first, models later

**Risk mitigation**:

- Asset pipeline delays don't block release
- Can ship "prototype" version if needed
- Gameplay feels good = art enhances it
- Gameplay feels bad = art can't fix it

---

## III. System Interactions

### How Patterns Compose

**Quest completion triggers entire pipeline (Dialogic-first path)**:

1. Player triggers QuestTrigger (Pattern 6: primitives)
2. QuestTrigger starts Dialogic timeline via DialogSystem (Pattern: Dialogic integration)
3. Dialogic shows approach options (Pattern 4: variants)
4. Player chooses approach
5. Dialogic emits signal → DialogSystem parses → calls GameStateActions.complete_quest
6. GameState.dispatch → QuestSystem.complete_quest (Pattern 1: immutable state)
7. QuestSystem loads quest JSON via DataLoader (Pattern 5: content separation)
8. QuestSystem applies degrades/rewards via PlayerSystem/world reducers (Pattern 2: degradation)
9. GameState emits state_changed signal
10. Quest completion may trigger a thought timeline (Pattern 3: thoughts→character)
11. Thought Dialogic timeline runs; options call GameStateActions.modify_conviction / modify_flexibility
12. Convictions/flexibility update; future options gate based on these stats (Pattern 2: funnel)

**Every pattern serves the core mechanic**: Dialogic handles how choices are presented; reducers + JSON data define what those choices mean for the character.

---

### Data Flow Diagram

**Input Layer**:

Player presses 'E' on QuestTrigger

↓

QuestTrigger: - If timeline_id set → DialogSystem.start_timeline(timeline_id) - Else → direct QuestSystem.start_quest (fallback)

**Dialogue / Flow Layer (Dialogic)**:

Dialogic timeline runs (quest or thought)

↓

Player chooses option

↓

Dialogic emits signal_event string (e.g. "complete_quest:join_rebels:diplomatic")

↓

DialogSystem parses signal and calls GameStateActions.\*

**Logic Layer**:

GameStateActions: - start_quest(...) - complete_quest(..., approach) - modify_conviction(...) - modify_flexibility(...) - can_start_quest(...)

↓

GameState.dispatch(reducer)

↓

QuestSystem / PlayerSystem: - QuestSystem loads quest JSON via DataLoader.get_quest(...) - Apply prerequisites, degrades, rewards, outcomes - Update convictions / flexibility / world flags

↓

GameState updates internal \_state

↓

GameState emits state_changed(new_state)

**Presentation Layer**:

UI listens to state_changed: - Updates HUD / quest log / debug overlay - Color/appearance updates from state

DialogSystem: - Starts/stops Dialogic timelines based on meta in state

**Key insights**:

Dialogic + DialogSystem form a front-end flow layer that never mutates state directly; they only call GameStateActions.

The logic layer (GameState + systems + DataLoader + JSON) remains the single source of truth.

Presentation (UI, visuals, Dialogic widgets) only reacts to state_changed; it never drives mechanics except via the sanctioned GameStateActions API.

---

## IV. Design Decisions

### Why Godot 4.5?

**Considered alternatives**:

- Unity: More mature, but overkill for 2D/simple 3D
- Unreal: Too heavy for indie scope
- Custom engine: Not realistic for solo dev

**Godot advantages**:

- Free, open-source
- GDScript = Python-like (AI agents understand)
- Built-in node system maps to our architecture
- WebGL export works well
- Active community, improving rapidly

---

### Why Dialogic 2.0?

**Alternative considered**: Roll our own dialogue system

**Dialogic advantages**:

- Visual editor for writers
- Built-in save/load
- Timeline system = quest flows
- Signal emission = hooks for our state
- Maintained by community

**Integration strategy**:

- Dialogic handles presentation only
- Never let Dialogic directly modify game state
- DialogSystem acts as bridge to GameStateActions
- All mechanical effects go through reducer pattern
- **Hybrid syntax**: Signals for mutations (`[signal arg="..."]`), `do` for queries (`do GameStateActions.get_*`)
  - Signals: Parsed by DialogSystem, dispatched through GameState, logged
  - Queries: Direct method calls on GameStateActions, read-only, no logging overhead
  - Architecture: Maintains immutability (signals) while enabling reactive content (queries)

---

### Why Not ECS (Entity-Component-System)?

**ECS advantages**:

- Great for thousands of entities
- Cache-friendly for physics/AI
- Popular in modern engines

**Why we didn't use it**:

- Overkill for <100 entities on screen
- Harder to serialize/save
- Functional patterns more intuitive for state
- AI agents less familiar with ECS

**Decision**: YAGNI (You Ain't Gonna Need It). Our scale doesn't require ECS complexity.

---

## V. Review and Specification Guidelines

### Philosophy: Define WHAT and WHY, Not HOW

Your role is to ensure architectural integrity through requirements, not implementations. CODER has creative freedom within constraints.

**CRITICAL RULES:**

1. **Specify requirements, NOT implementations** - Say "Use resolution timeline when quest active", NOT "Call \_select_timeline_for_quest_status() on line 85"
2. **Verify APIs before assuming** - Check Godot/Dialogic docs via context7 MCP, don't assume methods exist
3. **Only restrict when pattern at risk** - Intervene for immutability violations, not coding style

---

## VI. Test Quality Guidelines

### Philosophy: Tests as Living Documentation

Tests aren't just safety nets—they're executable specifications that teach CODER how systems should work. A good test tells a story.

Consult @../../test/CLAUDE.md on how to write effective tests. Maintain this document even when not explicitly state. It is the team's living-memory.

## VI. Known Risks & Mitigation

### Risk List

**1. Save file compatibility breaks**

**Symptom**: Old saves crash when loaded

**Prevention**:

- Version every save file
- Write migration functions for schema changes
- Never remove fields, only deprecate

**Mitigation if it happens**:

- Add compatibility layer
- Provide "update save" tool
- Clear communication about breaking changes

---

**2. Performance degradation from state duplication**

**Symptom**: Frame drops during state updates

**Prevention**:

- Profile before optimizing
- Lazy evaluation where possible
- Consider COW (copy-on-write) for large state sections

**Mitigation if it happens**:

- Selective mutability for hot paths (document why!)
- State diffing instead of full duplication
- Move heavy calculations out of frame

---

**3. Softlock from stat degradation**

**Symptom**: Player has 0/10 all stats, quest has no valid approach

**Prevention**:

- Every quest has "desperate" approach (no requirements)
- Integration tests verify 0-stat playthroughs
- Degradation caps at reasonable minimums

**Mitigation if it happens**:

- Patch adjusts approach requirements
- Add more "desperate" approaches
- Consider stat floor (can't go below 3?)

---

**4. Mystery too opaque**

**Symptom**: Players frustrated they don't know why options locked

**Prevention**:

- Grayed-out options show requirements on hover
- NPC occasionally comments on player's reputation
- Thought choices hint at consequences

**Mitigation if it happens**:

- Add optional "show conviction counters" toggle
- Patch in more explicit NPC feedback
- Consider small tutorial pop-ups

---

**5. AI agents generate inconsistent code**

**Symptom**: New system doesn't follow patterns, breaks tests

**Prevention**:

- AGENTS.md is source of truth
- Every PR requires: lint pass, test pass, human review
- Reject any code that doesn't match patterns

**Mitigation if it happens**:

- Refactor to match patterns immediately
- Update AGENTS.md if pattern needs evolution
- Add architectural validation tests

---

## VIII. Success Metrics

### What "Success" Looks Like

**Mechanical success**:

- Playtesters report feeling "I became something"
- Playthroughs with different stats feel distinct
- Combat serves narrative (not distraction)
- No softlocks in 10+ hour playthrough

**Narrative success**:

- Players discuss character arc, not stats
- Endings feel earned, not arbitrary
- NPC reactivity noticed and appreciated
- Story coherent despite approach variants

**Technical success**:

- 60 FPS on mid-range hardware
- Save/load under 2 seconds
- No progression-blocking bugs
- Modding community emerges

### Metrics to Track

**Quantitative**:

- Completion rate (target: 30%+)
- Average playtime (target: 8-12 hours)
- Crash rate (target: <0.1%)
- Save corruption rate (target: 0%)

**Qualitative**:

- Reviews mention character transformation
- Streamers have "oh no, what have I become" moments
- Forums discuss different build paths
- Fan art depicts character degradation

---

## IX. Comparison to Inspirations

### How We Differ From Our Influences

**Disco Elysium**:

- Inspiration: Thoughts shape character, internal dialogue
- Difference: We hide the stats, no skill checks visible
- Scope: Simpler dialogue (no full VO), more combat

**Gothic 2**:

- Inspiration: Faction reputation, atmospheric world
- Difference: Inverted power curve, no traditional leveling
- Scope: Smaller world, denser content

**Planescape: Torment**:

- Inspiration: Becoming through choice, philosophical themes
- Difference: Mechanical transformation, not just narrative
- Scope: Linear story vs. Torment's branching

**Darkest Dungeon**:

- Inspiration: Stress/degradation mechanics, gothic tone
- Difference: Permanent character change, not roster management
- Scope: Single character focus vs. party management

**Hades**:

- Inspiration: Room-based encounters, tight action
- Difference: Pause mechanic, abilities tied to character arc
- Scope: Gothic 2 level combat (simpler than Hades polish)

**Our unique contribution**:

- **Inverted progression**: Start powerful, lose options
- **Hidden accumulation**: Convictions shape character invisibly
- **Mechanical narrative**: Story told through gating, not text

---

## X. Philosophy

### Design Mantras

**"Mechanics first, narrative second"**

- If degradation doesn't work mechanically, no amount of writing fixes it
- Conversely, good mechanics make simple narrative powerful

**"Mystery over transparency"**

- Players should discover, not calculate
- Exact numbers kill roleplay
- Surprise is more valuable than optimization

**"Constraint breeds creativity"**

- Fewer options = more meaningful choices
- "You can't do X anymore" > "You can do X or Y or Z"
- Specialization > generalist power fantasy

**"Ship the prototype"**

- If gameplay works with primitives, it works
- Assets are polish, not prerequisites
- Playable > pretty

---

### When to Break the Rules

**This architecture is not dogma.** Break patterns when:

**Performance requires it**:

- If state duplication causes frame drops, optimize carefully
- Profiling > theory

**Player experience demands it**:

- If mystery causes mass confusion, add transparency
- Players > design purity

**Development velocity needs it**:

- If AI agents can't follow patterns, simplify
- Shipping > perfect architecture

**But**: Document every deviation. Future you needs to know why.

---

## XI. Conclusion

**This architecture exists to serve one goal**: Let players experience becoming something through accumulated choices.

Every pattern, every decision, every tradeoff aims at that experience.

- **Immutable state** makes degradation trackable
- **Data-driven content** makes variants scalable
- **Placeholder-first** validates mechanics early
- **Linear story** keeps scope manageable
- **Hidden convictions** preserve mystery
- **Degradation** creates the funnel

**If a feature doesn't serve this goal, cut it.**

**The game succeeds if**: A player finishes and thinks "I became a monster/hero/something, and I didn't see it happening until it was too late."

That's the experience this architecture enables.
