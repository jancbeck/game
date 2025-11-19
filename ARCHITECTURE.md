# Gothic-Inspired Degradation RPG - Architecture

**Version**: 1.0

**Purpose**: Design rationale and architectural decisions

**Audience**: Human developers, future maintainers

---

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
- This game: "You start with potential, choices define you" (novel)

**Mechanical justification**:

- Early game: Overwhelming options teach mechanics
- Mid game: Narrowing options create tension
- Late game: Constrained options feel earned, not frustrating

**Psychological model**:

```
Player expectation: "I'm getting stronger"
Actual experience: "I'm becoming something specific"
Realization: "Oh, this is about identity, not power"
```

**Design risk**: Players quit if they don't understand it's intentional.

**Mitigation strategy**:

1. Tutorial explicitly teaches degradation
2. Visual feedback (color change) reinforces consequences
3. Every quest has "desperate" option (no softlocks)
4. Ending validates whatever character emerged

---

### Pattern 3: Thoughts → Words → Actions → Character Pipeline

**Why hide conviction counters from player?**

**With visible numbers**:

```
Player sees: "Violence: 23/100"
Player thinks: "I need 3 more violence for this option"
Result: Optimization, not roleplay
```

**With hidden numbers**:

```
Player sees: [Threaten] option greyed out
Player thinks: "Why can't I do this anymore? I wasn't violent... was I?"
Result: Self-reflection, emergent narrative
```

**The funnel metaphor**:

- Wide top (Act 1): Many thoughts, many actions, flexibility
- Narrow middle (Act 2): Patterns emerge, options narrow
- Point bottom (Act 3): "This is who I am now"

**Implementation**:

- Thoughts increment hidden counters (violence_thoughts)
- Counters gate dialogue options (requires violence ≥ 3)
- Player discovers constraints organically
- No UI shows exact numbers (only flexibility stats)

---

### Pattern 4: Linear Story with Reactive Flavor

**Why not branching narrative?**

**Branching exponential growth**:

```
3 story beats with 3 branches each = 27 possible paths
Developer creates content for 27 paths
Player experiences 1 path
26 paths wasted
```

**Linear with flavor**:

```
3 story beats, single path
Each beat has 3 approach variants
Developer creates 9 approaches
Player experiences 1 flavored path
Feels unique without exponential cost
```

**Content efficiency**:

- Gothic 2: ~30 main quests, mostly linear, feels open
- Disco Elysium: Fully linear, incredible reactivity, feels branching
- Our target: Linear backbone + NPC memory + approach variants

**Example**:

```
Story Beat: "Confront the High Priest"
  - Violent approach: Fight, priest hostile
  - Diplomatic approach: Negotiate, priest wary
  - Stealthy approach: Ambush, priest surprised

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

```markdown
# data/quests/rescue_prisoner.md

---

## id: rescue_prisoner

# Rescue the Prisoner

Save the rebel from the dungeon.
```

Benefits:

- Typo = edit text file, reload
- Writers edit Markdown/YAML
- Localization = translate .md files
- Modding = drop in new .md files

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

**Quest completion triggers entire pipeline**:

```
1. Player triggers QuestTrigger (Pattern 6: primitives)
2. UI shows approach options (Pattern 4: variants)
3. Player chooses approach
4. QuestSystem.complete_quest dispatches (Pattern 1: immutable state)
5. DataLoader loads quest .md (Pattern 5: content separation)
6. Stats degrade (Pattern 2: degradation)
7. Thought scene triggers (Pattern 3: thoughts→character)
8. Player chooses thought
9. Conviction counter increments (Pattern 3: hidden)
10. Future options gate based on convictions (Pattern 2: funnel)
```

**Every pattern serves the core mechanic**: Choices accumulate invisibly into character transformation.

---

### Data Flow Diagram

```
Input Layer:
  Player presses 'E' on QuestTrigger
    ↓
Logic Layer:
  QuestTrigger dispatches to GameState
    ↓
  GameState calls QuestSystem.complete_quest
    ↓
  QuestSystem loads data via DataLoader
    ↓
  QuestSystem modifies state via PlayerSystem
    ↓
  GameState emits state_changed signal
    ↓
Presentation Layer:
  UI updates from state
  Player color changes from state
  Debug overlay shows stats
```

**Key insight**: Logic layer never touches presentation layer. Unidirectional flow only.

---

## IV. Design Decisions

### Why Godot 4.5?

**Considered alternatives**:

- Unity: More mature, but overkill for 2D/simple 3D
- Unreal: Too heavy for indie scope
- Custom engine: Not realistic for solo dev

**Godot advantages**:

- Free, open-source
- GDScript similar to Python (AI-friendly)
- Fast iteration (no compilation)
- Built-in scene system (perfect for primitives)
- Lightweight (good for primitives)

**Godot 4.5 specific features used**:

- Static variables (singleton state without autoload complexity)
- Typed dictionaries (safety without C#)
- Binary export (light obfuscation)

---

### Why GDScript over C#?

**Initially considered C# for**:

- Strong typing
- Better IDE support
- Familiar to many developers

**Chose GDScript because**:

- No compilation step (faster iteration)
- AI coding agents have more training data (Python-like syntax)
- Godot-first language (better documentation)
- Static typing added in 4.x (closes gap with C#)

**Decision**: GDScript's iteration speed > C#'s type safety for this project.

---

### Why No Branching Story?

**Evaluated story structures**:

**Full branching** (Witcher 3):

- 50+ hours development per branch
- Players see 20% of content
- Our capacity: 1 branch

**Hub-based** (Mass Effect):

- Choose mission order
- Ending based on choices
- Still requires multiple ending sequences

**Linear with reactivity** (Disco Elysium):

- Single path
- Heavy NPC reactivity
- Efficient content usage

**Decision**: Linear backbone + NPC memory flags = 80% of branching feel, 20% of development cost.

---

### Why Action-with-Pause Combat?

**Evaluated combat styles**:

**Turn-based** (Baldur's Gate 3):

- Easier to balance
- Better for tactics
- But: Slower pacing, complex UI

**Real-time** (Hades):

- Exciting, visceral
- Harder to balance
- But: Requires polish, animation

**Action-with-pause** (Transistor):

- Balance of both
- Pause = tactical depth
- Real-time = excitement
- But: Less common, harder to explain

**Decision**: Pause mechanic allows tactical play with primitive graphics. Real-time keeps energy up between story beats.

---

## V. Failure Modes & Prevention

### Identified Risks

**1. Players don't understand degradation is intentional**

**Symptom**: "This game is broken, my stats are going DOWN!"

**Prevention**:

- Tutorial explicitly teaches mechanic
- Early quest shows visible consequence
- Debug UI available to see exact numbers (if confused)
- Every approach always available ("desperate" option)

**Mitigation if it happens**:

- Patch adds more tutorial explanation
- Consider making flexibility visible (toggle option)

---

**2. Content explosion from reactivity**

**Symptom**: NPC has 50 dialogue variants, each 5% different

**Prevention**:

- Shared dialogue + 2-3 line variants only
- Memory flags are binary (not counters)
- "Guards hostile" flag changes 3 lines, not entire conversation

**Mitigation if it happens**:

- Audit content for duplication
- Merge similar variants
- Accept less reactivity in late-game

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

## VI. Evolution & Extensibility

### Post-Launch Extensions

**High-value, low-cost additions**:

- New side quests (just add .md files)
- New thought scenes (just add .json files)
- New items (just add .json files)
- UI themes/skins

**Medium-cost additions**:

- New Act (requires new story beats, NPCs)
- New combat abilities (requires balance tuning)
- New enemy types (requires AI behaviors)

**High-cost/avoid**:

- New core stats (breaks entire degradation system)
- Multiplayer (architecture not designed for it)
- Procedural generation (content is handcrafted)

---

### Modding Philosophy

**If we enable modding**:

- Data files are open (quests, dialogues)
- Code is obfuscated (systems are closed)
- Rationale: Content mods = yes, cheat mods = no

**Mod types we'd support**:

- Total conversions (replace all quests/dialogues)
- Side quest packs (add to existing game)
- Difficulty mods (adjust stat degradation rates)
- Translation mods (localize content)

**Mod types we wouldn't support**:

- Code mods (binary GDScript prevents this)
- Multiplayer mods (architecture incompatible)
- Save editors (could break validation)

---

## VII. Success Metrics

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

- 60 FPS on modest hardware
- Zero crashes in full playthrough
- Save/load flawless
- AI-generated code requires minimal fixes

**Development success**:

- Solo dev + AI agents complete in 9 months
- Budget under $X (define based on your goals)
- Scope didn't creep beyond architecture
- Could ship with primitives if needed

---

### Measuring Against Goals

**Primary goal**: "Mechanically-driven character arc"

**Validation**:

- Do choices accumulate into character? → Post-launch survey
- Do players feel transformation? → Playtest feedback
- Is mechanic novel? → Compare to existing RPGs

**If not achieved**:

- Degradation too subtle → Increase stat loss
- Mystery too opaque → Add feedback
- Linear story too obvious → Add more variants

---

## VIII. Comparisons

### Inspirations & Differentiation

**Gothic 2**:

- Inspiration: Open-world feel, faction progression
- Difference: Linear story, degradation instead of leveling
- Scope: 50% of Gothic 2's complexity (per your brief)

**Disco Elysium**:

- Inspiration: Skill system gates dialogue, heavy reactivity
- Difference: Convictions hidden, simpler dialogue trees
- Scope: 25% of Disco's word count (~30k vs ~1M words)

**Hades**:

- Inspiration: Room-based encounters, tight action
- Difference: Pause mechanic, abilities tied to character arc
- Scope: Gothic 2 level combat (simpler than Hades polish)

**Our unique contribution**:

- **Inverted progression**: Start powerful, lose options
- **Hidden accumulation**: Convictions shape character invisibly
- **Mechanical narrative**: Story told through gating, not text

---

## IX. Philosophy

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

## X. Conclusion

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
