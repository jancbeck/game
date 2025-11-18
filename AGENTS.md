# Gothic-Inspired Degradation RPG - Core Architecture

**Version**: 1.0  
**Scope**: Isometric 3D action-RPG with character degradation mechanics  
**Playable without assets**: Yes (primitive shapes throughout development)
**Tech:** Godot 4.5.1 (Forward+), GDScript (typed), GDScript Toolkit 4.x, Git LFS for assets.

---

## I. Foundational Patterns

### Pattern 1: Immutable State Architecture

**Definition**: All game state exists in a single Dictionary. No system mutates state directly. All changes flow through pure reducer functions.

**Structure**:

```
GameState (static singleton)
  ├─ state: Dictionary (immutable)
  ├─ dispatch(reducer: Callable) → void
  └─ state_changed signal

Systems (stateless, pure functions)
  └─ reduce(old_state: Dictionary, action: Action) → Dictionary
```

**Implications**:

- Save system serializes one object
- Undo/redo = state history stack
- Multiplayer sync = state diff transmission
- Debugging = state snapshot comparison
- AI-generated systems cannot create hidden dependencies

**Validation criteria**:

- Can any system access another system's internal state? → Fail
- Can state be in contradictory configuration? → Fail
- Does reloading saved state restore exact gameplay? → Pass

**Example application**:

```
Player chooses dialogue option
  ↓
DialogueSystem.choose_response(state, choice_id)
  ↓
Returns new state with: dialogue_vars updated, thought_counters incremented
  ↓
GameState.dispatch() propagates changes
  ↓
UI reacts to state_changed signal
```

---

### Pattern 2: Character Degradation Engine

**Definition**: Player character flexibility decreases through play. Stats represent available options, not power. Actions increment "conviction counters" that gate future choices.

**Core mechanics**:

1. **Stat Inversion**: Stats start high (10/10), decrease with use

   - Traditional: Strength 1 → 10 (gaining power)
   - This game: Flexibility 10 → 3 (losing options)

2. **Thought Accumulation**: Hidden counters track behavioral patterns

   - violence_thoughts, deceptive_thoughts, compassion_thoughts
   - Incremented by internal monologue choices
   - Never displayed directly to player

3. **Option Gating**: Dialogue/action availability based on thresholds

   - "Negotiate" requires flexibility_charisma >= 5
   - "Threaten" requires violence_thoughts >= 3
   - Options disappear without explanation

4. **Cascade Effect**: Loss in one area forces specialization
   - Low charisma → more violence → further charisma loss
   - Creates emergent character arc through mechanics

**Implications**:

- Every choice must track which conviction it reinforces
- UI must show unavailable options (greyed out, not hidden)
- Endgame requires minimal stat configuration (avoid softlocks)
- Tutorial must establish "losing options is intended"

**Validation criteria**:

- Can player complete game with any final stat configuration? → Pass
- Do players understand why options disappeared? → Fail (mystery is intentional)
- Can player reverse degradation easily? → Fail (should be rare/costly)

**Data structure**:

```
state["player"]["flexibility"]: Dictionary[String, int]
  ├─ charisma: 10 → 0
  ├─ cunning: 10 → 0
  └─ empathy: 10 → 0

state["player"]["convictions"]: Dictionary[String, int] (hidden)
  ├─ violence_thoughts: 0 → 100
  ├─ deceptive_acts: 0 → 100
  └─ compassionate_acts: 0 → 100
```

---

### Pattern 3: Thoughts → Words → Actions → Character Pipeline

**Definition**: Four-layer system where each layer constrains the next, implementing the degradation cascade.

**Layer hierarchy**:

```
Layer 1: Internal Monologue
  ├─ Presented as "thought bubbles" between scenes
  ├─ Player selects thought → increments hidden conviction counter
  └─ No immediate visible consequence

Layer 2: Dialogue Options
  ├─ Filtered by: flexibility stats + conviction thresholds
  ├─ Choosing option → decrements flexibility stat
  └─ Some choices locked due to Layer 1 accumulation

Layer 3: Action Availability
  ├─ Quest solution methods gated by dialogue outcomes
  ├─ "Diplomatic solution" unavailable if insulted NPC
  └─ Violent solutions require violence conviction threshold

Layer 4: Character Identity
  ├─ NPC reactions reflect accumulated choices
  ├─ Self-dialogue changes tone (brute vs diplomat)
  └─ Ending variation based on final stat configuration
```

**Implications**:

- Internal monologue scenes must occur regularly (every 2-3 quests)
- Conviction thresholds must be opaque to player
- NPCs must reference player's "reputation" based on conviction totals
- Late-game should feel constrained, early-game should feel open

**Validation criteria**:

- Does player feel agency despite narrowing options? → Pass
- Can player predict exact consequences of thoughts? → Fail (should be mysterious)
- Does character feel "earned" by endgame? → Pass

**Implementation requirements**:

- Thought scenes are non-interactive cutscenes with choice menus
- Dialogue system queries both flexibility and convictions
- Quest system has "approach tags" (diplomatic, violent, cunning)
- NPC dialogue has variants for player archetypes

---

### Pattern 4: Linear Story with Reactive Flavor

**Definition**: Single critical path with identical story beats. Player choices change _how_ scenes play, not _which_ scenes occur.

**Structure**:

```
Critical Path (fixed sequence):
  Act 1: Arrival → Join Rebels → First Mission
  Act 2: Uncover Conspiracy → Infiltrate Clerics → Face King
  Act 3: Final Choice → Confrontation → Epilogue

Reactivity Layer (variable):
  ├─ NPC dialogue variants (12+ per major NPC)
  ├─ Scene approach methods (3-5 per story beat)
  ├─ Flavor text based on conviction profile
  └─ Epilogue slides (5-8 based on key choices)
```

**Key principle**: Same destination, different journey context

**Example**:

```
Story Beat: "Enter King's Throne Room"

High Charisma Path:
  - Talk past guards
  - King greets you as "the diplomat"
  - Conversation focuses on negotiation

High Violence Path:
  - Fight through guards
  - King greets you as "the brute"
  - Conversation focuses on threats

Both paths:
  - Reach throne room (same)
  - King reveals conspiracy (same)
  - Player must decide allegiance (same)
```

**Implications**:

- Content creation scales linearly (not exponentially)
- Every story beat must have minimum 3 approach variants
- "Branching" is flavor text + NPC memory flags, not alternate plots
- Endings share 80% content, differ in epilogue details

**Validation criteria**:

- Can player experience fundamentally different stories? → Fail (should feel different, not be different)
- Does every choice feel meaningful despite linearity? → Pass
- Could we swap approach paths without breaking story? → Pass

**Content requirements**:

- 12-15 mandatory story beats
- 3-5 approach variants per beat
- 20-30 side quests (optional, affect flavor)
- Single climax with 2-3 resolution options

---

### Pattern 5: Content-Code Separation

**Definition**: Zero narrative content exists in code. All story, dialogue, quests defined in structured data files. Code systems are generic interpreters.

**File structure**:

```
data/
  ├─ quests/
  │   └─ *.md (Markdown + YAML frontmatter)
  ├─ dialogues/
  │   └─ *.yarn (Yarn dialogue format)
  ├─ characters/
  │   └─ *.json (stats, relationships)
  ├─ items/
  │   └─ *.json (equipment, consumables)
  └─ world/
      └─ *.json (locations, events)
```

**Code responsibilities**:

- Load and parse data files
- Evaluate conditionals (if player.charisma >= 5)
- Execute state transitions (set quest complete)
- Never contain literal story text

**Implications**:

- Writers edit Yarn/Markdown, never touch GDScript
- Adding quest = add one .md file, zero code changes
- AI generates content from narrative descriptions
- Localization = translate data files only
- Modding = user-added data files

**Validation criteria**:

- Can writer add entire quest without programmer? → Pass
- Does code contain any dialogue strings? → Fail
- Can we swap out all story content without code changes? → Pass

**Format specifications**:

**Quests** (Markdown + YAML):

```markdown
---
id: rescue_prisoner
act: 2
prerequisites: [joined_rebels]
approaches:
  violent: { requires: { violence: 3 }, degrades: { charisma: -2 } }
  stealthy: { requires: { cunning: 5 }, degrades: { charisma: -1 } }
---

# Quest: Rescue the Prisoner

[Description text]

## Approaches

[Approach descriptions]
```

**Dialogues** (Yarn):

```yarn
title: NPC_Greeting
---
NPC: Hello, stranger.
[[Be polite|Polite]] {requires: charisma >= 5}
[[Be rude|Rude]]
```

---

### Pattern 6: Placeholder-First Development

**Definition**: Game achieves full playability using primitive 3D shapes before any final assets exist. Assets are last-phase polish, not concurrent development.

**Primitive asset library**:

```
Characters:
  - Player: Blue capsule (height: 2m)
  - NPCs: Colored cubes (1m) - red=hostile, green=friendly, yellow=neutral
  - Enemies: Red cylinders (varying heights)

World:
  - Rooms: Grey GridMap planes + boundary cubes
  - Interactive objects: Colored spheres (0.5m)
  - Doors: Tall blue rectangles
  - Items: Small spheres (0.3m) with emission

UI:
  - Godot Control nodes with solid colors
  - Text-only dialogue boxes
  - Numbered stat displays
```

**Development phases**:

1. **Phase 1 (Months 1-3)**: Core systems + full story in primitives
2. **Phase 2 (Months 4-6)**: Combat + player feedback in primitives
3. **Phase 3 (Months 7-9)**: Asset replacement (piecemeal, non-blocking)

**Implications**:

- Gameplay validated before asset investment
- Art budget overruns don't block release
- Playtesting begins immediately
- Asset pipeline is hot-swappable
- Can ship "prototype" version if needed

**Validation criteria**:

- Can external playtester complete game with primitives? → Pass
- Does primitive version feel like "a game" or "a demo"? → Should feel like a game
- Do assets change core mechanics? → Fail (should be cosmetic)

**Technical requirements**:

- All entities use MeshInstance3D with basic shapes
- Materials use solid colors + optional emission
- Animations use simple transforms (no skeletal animation until Phase 3)
- Asset references stored in data layer, not hardcoded

---

## II. System Design Specifications

### Combat System: Action-with-Pause

**Pattern**: Real-time movement + ability execution, pausable for tactical decisions

**Core loop**:

```
1. Player enters combat arena (room transition)
2. Enemies spawn based on player conviction profile
3. Real-time:
   - WASD movement (no physics except boundaries)
   - Left-click: basic attack (no cooldown)
   - Mouse aim determines direction
4. Abilities (1-4 keys):
   - Press key → time slows to 20% (not full pause)
   - Show AOE indicator + remaining cooldown
   - Confirm or cancel
5. Victory condition: all enemies defeated
6. Defeat condition: player health = 0
```

**Degradation integration**:

- Available abilities filtered by conviction thresholds
- High violence: more melee options
- High cunning: more crowd control
- High empathy: healing/support abilities
- Abilities literally disappear from hotbar as stats decay

**Implications**:

- No complex animation state machines needed (primitives = simple rotations)
- Difficulty scales by limiting player options, not increasing enemy stats
- Combat feels different for "brute" vs "diplomat" characters
- Can be fun with placeholder graphics (colored projectiles, simple hitboxes)

**Validation criteria**:

- Does combat teach player about character degradation? → Pass
- Can player with minimal stats still defeat encounters? → Pass
- Does combat feel like "action" not "puzzle"? → Pass

**Primitive implementation**:

- Player: Blue capsule, rotates to face mouse
- Enemies: Red cylinders, move toward player
- Projectiles: Colored spheres (blue=player, red=enemy)
- AOE: Wireframe circle on ground
- Abilities: Icons = colored squares with numbers

---

### Quest System: Approach-Based Resolution

**Pattern**: Every quest has 3-5 solution methods, all reach same outcome, differ in flavor and degradation costs

**Quest structure**:

```
Quest Node
  ├─ Objective (fixed): "Rescue prisoner"
  ├─ Approaches (3-5 options):
  │   ├─ Violent: Fight guards
  │   ├─ Stealthy: Sneak through sewers
  │   ├─ Diplomatic: Bribe warden
  │   └─ Desperate: Get captured intentionally
  ├─ Completion Trigger (same for all)
  └─ Consequences (per-approach):
      ├─ Stat degradation
      ├─ NPC memory flags
      └─ Item rewards
```

**Approach gating**:

- Each approach requires minimum stat/conviction thresholds
- Late-game quests have fewer available approaches
- "Desperate" approaches always available (failsafe)

**Implications**:

- No quest has single solution
- Player cannot be softlocked
- Degradation system creates organic difficulty curve
- Replayability = different approach paths, not different stories

**Validation criteria**:

- Can player with all stats at 0 still complete every quest? → Pass
- Do all approaches feel distinct? → Pass
- Does approach choice affect later quests? → Only via NPC memory flags

**Data specification**:

```yaml
approaches:
  violent:
    requires: { violence_thoughts: 3 }
    degrades: { flexibility_charisma: -2, violence_thoughts: +2 }
    memory_flags: [guards_hostile, reputation_brutal]
  diplomatic:
    requires: { flexibility_charisma: 5 }
    degrades: { flexibility_charisma: -1 }
    memory_flags: [guards_respect, reputation_smooth]
```

---

### Dialogue System: Yarn-Based Conditional Trees

**Pattern**: Branching dialogue defined in Yarn format, evaluated against game state at runtime

**Yarn structure**:

```yarn
title: MerchantNegotiation
---
<<if visited("InsultedMerchant")>>
  Merchant: Get out. I don't deal with your kind.
  -> END
<<endif>>

Merchant: What do you want?

[[I want to trade|Trade]] <<if $flexibility_charisma >= 5>>
[[Hand over your goods|Threaten]] <<if $violence_thoughts >= 3>>
[[Never mind|Exit]]

===
title: Threaten
---
<<set $flexibility_charisma -= 1>>
<<set $violence_thoughts += 1>>
<<set $visited_InsultedMerchant = true>>

You: Give me your best items. Now.
Merchant: [backs away fearfully]
-> CombatEncounter
```

**Conviction tracking in dialogue**:

- Choices increment hidden conviction counters
- Choices decrement flexibility stats
- Future dialogue nodes query these values
- NPCs remember choices via flags

**Implications**:

- Writers use Yarn syntax (simpler than JSON)
- Conditionals = natural language: `if charisma >= 5`
- Variables auto-sync with game state
- AI can generate Yarn from conversation descriptions

**Validation criteria**:

- Can every story beat be reached? → Pass
- Do convictions properly gate dialogue? → Pass
- Can player see ALL dialogue in one playthrough? → Fail (intended)

**Technical requirements**:

- YarnSpinner-Godot plugin
- Custom functions: `visited()`, `get_conviction()`, `has_item()`
- State sync: Yarn variables ↔ GameState dictionary

---

### Internal Monologue System

**Pattern**: Periodic cutscenes where player chooses thoughts that increment hidden conviction counters

**Trigger conditions**:

- After every 2-3 main quests
- At act transitions
- Before major story decisions

**Structure**:

```
1. Screen fades to black
2. Text appears: Player's internal voice
3. 2-4 thought options presented
4. Player selects one
5. Hidden conviction counter increments
6. Return to gameplay (no visible change)
```

**Example**:

```
Scene: After killing bandit leader

Internal voice: "That was necessary. Wasn't it?"

Thoughts:
A) "He deserved it. The world is better without him."
   → violence_thoughts +2, empathy_thoughts -1

B) "I did what I had to. I don't enjoy this."
   → violence_thoughts +1

C) "There had to be another way. I'm becoming something I hate."
   → empathy_thoughts +1, violence_thoughts -1
```

**Implications**:

- No right/wrong choices (all are valid)
- Player doesn't see numerical impact
- Later realizes choices affected available options
- Creates metacognitive gameplay (thinking about thinking)

**Validation criteria**:

- Are thought choices meaningful? → Pass
- Can player predict exact impact? → Fail (mystery is key)
- Do thoughts align with action opportunities later? → Pass

---

## III. Data Architecture

### State Schema

```gdscript
GameState.state: Dictionary = {
    "player": {
        "position": Vector3,
        "health": int,
        "max_health": int,

        "flexibility": {
            "charisma": int,  # 0-10, decreases with use
            "cunning": int,
            "empathy": int
        },

        "convictions": {  # Hidden from player
            "violence_thoughts": int,
            "deceptive_acts": int,
            "compassionate_acts": int
        },

        "inventory": Array[String],  # Item IDs
        "equipment": {
            "weapon": String,
            "armor": String
        }
    },

    "world": {
        "current_location": String,
        "act": int,

        "npc_states": Dictionary[String, {
            "alive": bool,
            "relationship": int,
            "memory_flags": Array[String]
        }],

        "location_flags": Dictionary[String, bool]
    },

    "quests": Dictionary[String, {
        "status": String,  # "available", "active", "completed", "failed"
        "approach_taken": String,
        "objectives_completed": Array[String]
    }],

    "dialogue_vars": Dictionary[String, Variant],  # Yarn variable sync

    "combat": {
        "active": bool,
        "enemies": Array[Dictionary],
        "available_abilities": Array[String]  # Filtered by convictions
    },

    "meta": {
        "playtime_seconds": int,
        "save_version": String,
        "current_scene": String
    }
}
```

---

### Content File Formats

**Quest Definition** (`data/quests/*.md`):

```markdown
---
id: infiltrate_temple
act: 2
location: cleric_temple
prerequisites:
  - completed: discover_conspiracy
  - npc_alive: rebel_contact

approaches:
  violent:
    label: "Fight through the main entrance"
    requires:
      violence_thoughts: 5
    degrades:
      flexibility_charisma: -2
      flexibility_empathy: -1
    rewards:
      convictions:
        violence_thoughts: +3
      memory_flags:
        - temple_hostile
        - guards_dead

  stealthy:
    label: "Sneak through service tunnels"
    requires:
      flexibility_cunning: 6
    degrades:
      flexibility_cunning: -1
    rewards:
      convictions:
        cunning: +2
      memory_flags:
        - temple_unaware

  desperate:
    label: "Surrender and get captured"
    requires: {} # Always available
    degrades:
      flexibility_charisma: -1
      flexibility_empathy: -1
    rewards:
      memory_flags:
        - temple_captured
        - reputation_weak

outcomes:
  all: # Regardless of approach
    - advance_to: confront_high_priest
    - unlock_location: temple_inner_sanctum
---

# Infiltrate the Temple

The clerics are hiding something. You need to get inside their temple and discover what they're planning.

## Violent Approach

Storm the main gate. Your reputation precedes you - they'll know you're coming.

## Stealthy Approach

A rebel contact knows about service tunnels. Requires precise timing and nerves of steel.

## Desperate Approach

Let them capture you. Risky, but you'll get inside either way.
```

**Dialogue Definition** (`data/dialogues/*.yarn`):

```yarn
title: HighPriestConfrontation
tags: main_story act2
---
<<if visited("HighPriestConfrontation")>>
    HighPriest: You again? You never learn.
    -> SecondEncounter
<<endif>>

<<if $world.npc_states.temple_guards.memory_flags contains "guards_dead">>
    HighPriest: You murdered my guards. There will be no mercy.
    -> HostileConfrontation
<<elseif $world.npc_states.temple_guards.memory_flags contains "temple_unaware">>
    HighPriest: How did you... no matter. You're here now.
    -> NeutralConfrontation
<<else>>
    HighPriest: So, you've come willingly. Interesting.
    -> CuriousConfrontation
<<endif>>

===

title: NeutralConfrontation
---
HighPriest: You want answers. I can respect that.

Player: Why are you working with the King?

HighPriest: [reveals conspiracy]

[[Attack him now|ViolentResolution]] <<if $player.convictions.violence_thoughts >= 7>>
[[Demand he stand down|DiplomaticResolution]] <<if $player.flexibility.charisma >= 4>>
[[Try to reason with him|EmpatheticResolution]] <<if $player.flexibility.empathy >= 3>>
[[Just listen|PassiveResolution]]

===

title: ViolentResolution
---
<<set $player.flexibility.empathy -= 2>>
<<set $player.convictions.violence_thoughts += 2>>

You: [Draw weapon] This ends now.

HighPriest: So be it.

-> CombatEncounter_HighPriest
```

**Character Definition** (`data/characters/*.json`):

```json
{
  "id": "high_priest",
  "name": "High Priest Aldric",
  "faction": "clerics",
  "initial_state": {
    "alive": true,
    "relationship": 0,
    "memory_flags": []
  },
  "dialogue_variants": {
    "greeting": {
      "default": "high_priest_neutral_greeting",
      "if_flags": {
        "guards_dead": "high_priest_hostile_greeting",
        "temple_unaware": "high_priest_surprised_greeting"
      }
    }
  },
  "combat_stats": {
    "health": 200,
    "abilities": ["holy_smite", "heal", "shield"]
  }
}
```

---

## IV. AI Agent Integration Points

### Code Generation Scope

**What AI agents generate**:

1. **System reducers** (`core/*_system.gd`):

   - Pure functions: `reduce(state: Dictionary, action) -> Dictionary`
   - Input: current state + action parameters
   - Output: new state with changes applied
   - Constraints: No side effects, no node access, fully testable

2. **Data validators**:

   - JSON schema enforcement
   - Quest prerequisite checking
   - Dialogue condition syntax validation

3. **Unit tests** (`tests/*.gd`):
   - GUT framework tests
   - Each test proves one edge case impossible
   - Generated from natural language specifications

**What AI agents DO NOT generate**:

- Narrative content (written by human)
- Godot scene structure (template-based)
- Core architecture (defined in this document)

---

### Content Generation Scope

**What AI agents generate**:

1. **Quest data files** from narrative descriptions:

   ```
   Input: "Player must infiltrate temple. Can fight, sneak, or surrender. Fighting makes clerics hostile later."
   Output: Complete quest .md file with approach definitions
   ```

2. **Dialogue trees** from conversation outlines:

   ```
   Input: "NPC greets player differently if they killed guards vs snuck past"
   Output: Yarn file with conditional branching
   ```

3. **Item definitions** from balance spreadsheets:
   ```
   Input: CSV with weapon stats
   Output: JSON files per item
   ```

**What AI agents DO NOT generate**:

- Main story beats (human-designed)
- Character arcs (human-written)
- Thematic elements (human-directed)

---

### Prompt Templates

**For system implementation**:

```
Generate GDScript class that:
- Extends RefCounted
- Contains only static functions
- Function signature: static func NAME(state: Dictionary, ...) -> Dictionary
- Uses typed parameters: Dictionary[String, Type]
- Returns new state (immutable update pattern)
- Includes docstring with example usage
- Include GUT test that proves: [EDGE CASE]

System: QuestSystem
Function: complete_quest(state: Dictionary, quest_id: String, approach: String) -> Dictionary
Edge case to prove impossible: Cannot complete quest if prerequisite quest is not completed
```

**For content generation**:

```
Generate quest definition file (.md format) from this description:

Quest: "Rescue the Prisoner"
Location: King's dungeons
Prerequisites: Player joined rebels
Approaches:
1. Violent - fight guards (requires violence_thoughts >= 3)
2. Stealthy - use sewers (requires flexibility_cunning >= 5)
3. Diplomatic - bribe warden (requires flexibility_charisma >= 7)

All approaches lead to: prisoner rescued, player advances to next story beat
Degradation costs: violent (-2 charisma), stealthy (-1 cunning), diplomatic (-1 charisma)

Output format: Markdown with YAML frontmatter as specified in Pattern 5
```

---

## V. Validation Framework

### Architectural Invariants

These must always be true. If violated, architecture is broken:

**State Management**:

- ✓ All game state accessible from `GameState.state`
- ✗ Any system stores state in member variables
- ✓ State transitions are pure functions
- ✗ Functions have side effects (file I/O, node modification)

**Degradation System**:

- ✓ Every player action affects flexibility/conviction counters
- ✓ All stat values within bounds (0-10 for flexibility)
- ✓ Player can complete game with any final stat configuration
- ✗ Dialogue options increase flexibility stats
- ✗ Convictions visible in UI

**Content-Code Separation**:

- ✓ All narrative text in data files
- ✗ GDScript contains literal dialogue strings
- ✓ Adding quest requires zero code changes
- ✗ Quest logic hardcoded in systems

**Placeholder Development**:

- ✓ Game fully playable with primitive shapes
- ✓ Asset paths in data layer, not hardcoded
- ✗ Gameplay blocked waiting for assets

---

### Testing Requirements

**Unit tests must prove** (tests/):

```gdscript
# Quest System
test_cannot_start_quest_without_prerequisites()
test_cannot_complete_quest_out_of_order()
test_quest_with_dead_npc_fails_gracefully()
test_all_approaches_reach_same_outcome()

# Degradation System
test_flexibility_never_exceeds_maximum()
test_flexibility_never_goes_negative()
test_conviction_accumulation_gates_dialogue()
test_zero_flexibility_still_has_available_options()

# Combat System
test_abilities_filtered_by_conviction_thresholds()
test_player_death_does_not_corrupt_state()
test_victory_triggers_correct_state_transition()

# Dialogue System
test_unavailable_option_does_not_appear()
test_conviction_requirement_properly_enforced()
test_npc_memory_affects_dialogue_variant()

# State Management
test_state_serialization_preserves_all_data()
test_state_deserialization_restores_exact_gameplay()
test_dispatch_never_mutates_original_state()
```

**Integration tests must prove**:

```gdscript
test_complete_quest_degradation_flow()
  # 1. Start quest
  # 2. Choose approach
  # 3. Complete quest
  # 4. Verify: stats degraded, convictions incremented, next quest unlocked

test_thought_to_action_pipeline()
  # 1. Choose violent thought
  # 2. Verify: dialogue option appears
  # 3. Choose dialogue option
  # 4. Verify: violent action available in quest

test_full_playthrough_with_minimal_stats()
  # Simulate player who degraded to minimum stats
  # Verify: game still completable via desperate options
```

---

### Milestone Validation

**Month 2 validation**:

- [x] All core systems implemented (state management, player movement, quest system, data loader)
- [x] Unit tests pass for state management, player system, quest system, and data loader
- [ ] Placeholder game playable start-to-finish
- [x] Save/load preserves exact state (Architecturally Sound, implementation pending)
- [ ] One complete story beat with all approach variants

**Month 4 validation**:

- [ ] Full story skeleton implemented (12-15 beats)
- [ ] All quests have 3+ approach options
- [ ] Combat encounters functional with primitives
- [ ] Degradation system creates meaningful choice constraints
- [ ] External playtester completes game with primitives

**Month 6 validation**:

- [ ] All dialogue trees complete
- [ ] Internal monologue system triggers correctly
- [ ] NPC reactivity reflects player choices
- [ ] Combat tuned for difficulty curve
- [ ] Polish pass on UI/feedback

**Month 9 validation**:

- [ ] Assets integrated (can be incomplete)
- [ ] Game shippable in current state
- [ ] Performance targets met (60 FPS)
- [ ] Save system robust across versions

---

## VI. Risk Mitigation

### Known failure modes and prevention:

**Softlock risk**: Player degradation leaves no viable options

- **Prevention**: Every quest has "desperate approach" (no requirements)
- **Validation**: Test suite runs with all stats at 0

**Mystery opacity**: Players don't understand degradation system

- **Prevention**: Tutorial explicitly teaches "losing options is intended"
- **Validation**: Playtest with fresh users, measure confusion rate

**Content explosion**: Reactivity creates exponential content needs

- **Prevention**: Flavor variants share 80% content, differ in 2-3 lines
- **Validation**: Track content-per-quest ratio, flag outliers

**Asset pipeline bottleneck**: Waiting for art blocks development

- **Prevention**: Placeholder-first development, assets are final phase
- **Validation**: Game must ship in primitive state if needed

**AI agent inconsistency**: Generated code doesn't follow patterns

- **Prevention**: Strict prompt templates + linter rules + test requirements
- **Validation**: Every PR must pass: type checks, unit tests, pattern linter

**Scope creep**: Feature additions violate core patterns

- **Prevention**: This document is contract, changes require architecture revision
- **Validation**: Weekly review: does new feature require state outside GameState?

---

## VII. Success Criteria

### The game succeeds if:

**Mechanical**:

- Degradation system creates emergent character arcs
- Players feel choices matter without seeing exact numbers
- Combat is functional and enjoyable with primitives
- Every story beat reachable regardless of stat configuration

**Narrative**:

- Linear story feels reactive and personalized
- Character "becomes" something through accumulated choices
- NPCs react meaningfully to player actions
- Ending feels earned, not arbitrary

**Technical**:

- Save/**Technical** (continued):
- Save/load works flawlessly across sessions
- 60 FPS maintained with 20+ entities on screen
- Zero crashes in 10+ hour playthrough
- AI-generated code integrates without manual rewrites

**Development**:

- Game playable end-to-end by Month 4
- Assets added incrementally without blocking progress
- Content additions require zero code changes
- Solo developer + AI agents complete in 9 months

**Player experience**:

- Players replay to explore different degradation paths
- "I became a monster without realizing it" moments occur naturally
- Frustration at lost options transitions to acceptance of character arc
- Combat doesn't distract from narrative focus

---

## VIII. Development Workflow

### Phase Breakdown

**Phase 1: Foundation (Months 1-2)**

**Deliverables**:

- [x] Core systems implemented (state management, player movement, quest system, data loader)
- [x] State management architecture validated
- [x] Unit test suite passing (all implemented tests)
- [x] Placeholder game playable start-to-finish
- [x] Save/load preserves exact state (Architecturally Sound, implementation pending)
- [ ] One complete story beat with all systems integrated (functional logic for one quest, but not yet integrated with full presentation/dialogue layers)

**Validation gates**:

- [x] Can AI agents generate system code from prompts? → Pass
- [x] Does degradation system gate options as designed? → Pass
- [x] Is state fully serializable/deserializable? → Pass (Architecturally Sound)
- [x] Can external reviewer understand architecture from this doc? → Pass

**AI agent tasks**:

- Generate system reducers from specifications
- Generate unit tests from edge case descriptions
- Generate initial data file templates

**Human tasks**:

- Write this architecture document
- Design core degradation formulas
- Create prompt templates for AI agents
- Review/integrate AI-generated code

---

**Phase 2: Story Skeleton (Month 3)**

**Deliverables**:

- All 12-15 story beats defined in quest files
- Complete dialogue tree for main story path
- World layout (rooms/locations) in primitives
- NPC character definitions
- First playthrough possible (rough)

**Validation gates**:

- Does story flow make sense start-to-finish? → Pass
- Are all quest approaches functional? → Pass
- Does degradation create meaningful late-game constraints? → Pass
- Can playtester complete without developer guidance? → Pass

**AI agent tasks**:

- Generate quest .md files from narrative descriptions
- Generate Yarn dialogue from conversation outlines
- Generate NPC JSON from character descriptions
- Validate data file consistency

**Human tasks**:

- Write story beat outlines
- Write main character arcs
- Design quest approach options
- Playtest and iterate on pacing

---

**Phase 3: Combat & Feel (Months 4-5)**

**Deliverables**:

- Combat system fully implemented
- Enemy AI behaviors functional
- Ability system with degradation integration
- Combat encounters balanced for difficulty curve
- Player feedback systems (hit reactions, UI updates)

**Validation gates**:

- Does combat feel "fun" with primitives? → Pass
- Do different stat configurations create different combat experiences? → Pass
- Can player with minimal stats still win encounters? → Pass
- Does combat serve narrative (not distract from it)? → Pass

**AI agent tasks**:

- Generate enemy behavior scripts from specifications
- Generate ability definitions from design docs
- Generate combat balance formulas
- Generate combat encounter configurations

**Human tasks**:

- Design ability progression
- Tune difficulty curve
- Design enemy types
- Playtest combat pacing

---

**Phase 4: Reactivity & Polish (Month 6)**

**Deliverables**:

- All NPC dialogue variants implemented
- Internal monologue system triggering correctly
- Memory flags affecting world state
- UI polish (still primitive graphics)
- Sound effect placeholders (simple beeps/tones)

**Validation gates**:

- Do NPCs react meaningfully to player choices? → Pass
- Does world feel reactive despite linear story? → Pass
- Are internal monologue moments impactful? → Pass
- Is feedback clear with primitive graphics? → Pass

**AI agent tasks**:

- Generate dialogue variants from base conversations
- Generate NPC reaction logic from memory flags
- Generate UI layout code from wireframes

**Human tasks**:

- Write dialogue variants
- Design internal monologue scenes
- Tune reactivity systems
- Polish UI/UX flow

---

**Phase 5: Content Complete (Month 7)**

**Deliverables**:

- All side quests implemented
- All optional content accessible
- Ending variations complete
- Tutorial/onboarding flow polished
- Save system robust

**Validation gates**:

- Is every piece of content reachable? → Pass
- Do multiple playthroughs feel distinct? → Pass
- Can players understand systems without external guidance? → Pass
- Is game "shippable" in primitive state? → Pass

**AI agent tasks**:

- Generate side quest content from descriptions
- Generate tutorial dialogue/prompts
- Validate content graph completeness

**Human tasks**:

- Write side quest narratives
- Design tutorial experience
- Final balancing pass
- External playtesting

---

**Phase 6: Asset Integration (Months 8-9)**

**Deliverables**:

- 3D models replacing character primitives
- Environment art replacing grey rooms
- Final UI graphics
- Music and sound effects
- Particle effects and polish

**Validation gates**:

- Do assets enhance experience without changing gameplay? → Pass
- Is performance still 60 FPS with final assets? → Pass
- Are assets consistent in style/quality? → Pass
- Could game ship without full asset completion? → Yes

**AI agent tasks**:

- Generate asset integration code (swap primitive for model)
- Generate material definitions
- Validate asset file formats

**Human tasks** (or AI asset generation):

- Generate/source 3D models
- Generate/source textures
- Generate/source audio
- Integrate piece-by-piece
- Polish pass

**Critical principle**: Assets are additive, not blocking. Game ships with mix of primitives/final assets if needed.

---

### Daily Workflow Pattern

**Morning** (Planning):

1. Review previous day's AI-generated code
2. Write specifications for today's AI tasks
3. Define validation criteria for outputs

**Midday** (Generation): 4. Submit prompts to AI coding agents 5. AI generates system code + tests 6. Review outputs against specifications 7. Integrate passing code, reject/revise failing code

**Afternoon** (Validation): 8. Run full test suite 9. Playtest new content in-game 10. Document issues/edge cases 11. Write next day's specifications

**Weekly** (Review):

- Architecture compliance audit (use Section V checklist)
- Playthrough test (start to current content end)
- Performance profiling
- Adjust timeline if needed

---

## IX. Technical Constraints

### Godot 4.5 Specific

**Leveraged features**:

- Static variables in GDScript (state singletons)
- Typed dictionaries/arrays (type safety)
- Binary GDScript export (obfuscation)
- AnimationMixer (combat animation)
- Multi-threaded navigation (world pathfinding)

**Avoided features**:

- Physics engine (use simple collision only)
- Complex shaders (primitives use solid materials)
- Skeletal animation (Phase 1-7, simple transforms only)
- Multiplayer/networking (single-player only)

**Performance targets**:

- 60 FPS minimum with 20 entities
- State transition < 16ms
- Save/load < 1 second
- Scene transition < 0.5 seconds

**File size targets**:

- Base game < 500MB (primitives)
- With assets < 2GB
- Save file < 1MB

---

### Code Quality Standards

**All code must**:

- Be formatted using `gdformat`.
- Pass `gdlint --type-check`
- Have type annotations on all parameters/returns
- Include docstring with example usage
- Have corresponding unit test
- Follow immutable state pattern (no mutation)

**AI-generated code must additionally**:

- Include comment block: "Generated by AI: [date] [prompt_id]"
- Pass human review before integration
- Not reference Godot nodes (core systems only)

**Forbidden patterns**:

- Global state outside GameState singleton
- Mutation of input parameters
- Node references in core systems
- Hardcoded narrative text
- Save data outside state dictionary

---

## X. Content Specifications

### Story Structure

**Act 1: Becoming** (4-5 quests, ~2 hours)

- Introduce degradation mechanics
- Player joins rebels
- First internal monologue
- Establish central conflict
- **Key theme**: "Who will you become?"

**Act 2: Consequences** (6-7 quests, ~3-4 hours)

- Options begin narrowing noticeably
- Player confronts other factions (clerics, king)
- Multiple internal monologues
- NPCs react to past choices
- **Key theme**: "Your choices have shaped you"

**Act 3: Identity** (3-4 quests, ~1-2 hours)

- Heavily constrained options
- Player faces consequences of degradation
- Final choice with limited approaches
- Ending reflects accumulated character
- **Key theme**: "This is who you are now"

**Estimated playtime**: 7-9 hours (main story only)

---

### Dialogue Density

**Per story beat**:

- 200-400 words base dialogue
- 3-5 player response options
- 2-3 NPC reaction variants (based on memory flags)
- 1 internal monologue moment (every 2-3 beats)

**Total estimated**:

- ~15,000 words main story dialogue
- ~5,000 words internal monologue
- ~10,000 words side quest dialogue
- **Total: 30,000 words** (manageable for solo writer)

**Comparison**:

- Gothic 2: ~40,000 words
- Disco Elysium: ~1,000,000 words
- Target: ~25% of Gothic 2's narrative complexity

---

### Quest Complexity

**Main quests** (12-15 total):

- 3-5 approach options each
- All approaches ~10-15 minutes to complete
- Clear objective, multiple paths
- Mandatory for story progression

**Side quests** (20-25 total):

- 2-3 approach options each
- 5-10 minutes to complete
- Optional, affect flavor only
- Provide extra character moments

**Quest structure template**:

```
1. Setup dialogue (introduce objective)
2. Approach selection (player chooses method)
3. Execution phase (gameplay happens here)
4. Resolution dialogue (NPC reacts to approach)
5. State update (degradation, flags, rewards)
```

---

### Combat Encounter Design

**Encounter types**:

1. **Story encounters** (12-15 total)

   - Scripted, tied to main quest beats
   - Enemies reflect player character (brutes for violent player)
   - Victory required for progression
   - ~2-3 minutes each

2. **Optional encounters** (20-30 total)
   - Room-based, player can avoid
   - Provide resources/loot
   - Scale difficulty to current act
   - ~1-2 minutes each

**Enemy variety**:

- 5-6 enemy types (primitives: different colored cylinders)
- Each type has 2-3 abilities
- AI behavior: melee rush, ranged kite, support healing

**Boss encounters** (3 total, one per act):

- 5-8 minutes each
- Multi-phase (health thresholds trigger new abilities)
- Require use of multiple ability types
- Story-significant (major character confrontations)

---

### Progression Curve

**Flexibility degradation**:

```
Start of game: All stats 10/10
After Act 1:   Average 8/10 (2 points lost across stats)
After Act 2:   Average 5/10 (5 points lost)
End of game:   Average 2-3/10 (7-8 points lost)
```

**Conviction accumulation**:

```
Start:  All convictions 0
Act 1:  One conviction reaches ~20
Act 2:  Dominant conviction reaches ~60
Act 3:  Dominant conviction 80-100, others 20-40
```

**Narrative impact**:

- Act 1: ~30% of dialogue options unavailable
- Act 2: ~60% of dialogue options unavailable
- Act 3: ~80% of dialogue options unavailable, but remaining options are meaningful

---

## XI. Extensibility Points

### Post-Launch Content

**Easy to add**:

- New side quests (just add .md file)
- New dialogue branches (just add .yarn file)
- New items/equipment (just add .json file)
- New NPC interactions (update character .json)

**Moderate difficulty**:

- New enemy types (requires combat balancing)
- New abilities (requires conviction threshold design)
- New locations (requires scene creation)

**Difficult/not recommended**:

- New core stats (requires system rewrites)
- New story acts (disrupts pacing)
- Multiplayer (architecture not designed for it)

---

### Modding Support

**Architecture naturally supports**:

- Total conversion mods (replace all data files)
- Quest mods (add .md files to data/quests/)
- Dialogue mods (add .yarn files)
- Character mods (replace .json definitions)

**To enable modding**:

1. Document data file formats
2. Create mod loading system (scan mods/ folder)
3. Provide content validation tool
4. Release without DRM/obfuscation (optional)

**Not supported**:

- Code mods (binary GDScript is obfuscated)
- Graphics mods (asset pipeline is internal)
- Save file editing (could break validation)

---

## XII. Documentation Requirements

### For AI Agents

**Must provide**:

- This architecture document
- Prompt templates (Section IV)
- Data format specifications (Section III)
- Example implementations of each pattern
- Test suite examples

### For Content Creators

**Must provide**:

- Quest writing guide (Markdown format)
- Dialogue writing guide (Yarn syntax)
- Character creation guide (JSON schema)
- Conviction/flexibility balance spreadsheet
- Story beat template

### For Players

**Must provide**:

- Tutorial that teaches degradation system
- In-game glossary (what stats mean)
- Control reference
- Save management instructions

**Must NOT provide**:

- Optimal build guides (defeats purpose)
- Conviction threshold numbers (mystery is key)
- "Correct" choice guides (all choices valid)

---

## XIII. Appendix: Pattern Examples

### Example: Pure Reducer Function

```gdscript
# core/quest_system.gd
class_name QuestSystem
extends RefCounted

## Completes a quest using specified approach.
## Returns new state with quest marked complete, stats degraded,
## and consequences applied.
##
## Example:
##   var new_state = QuestSystem.complete_quest(
##     state,
##     "rescue_prisoner",
##     "violent"
##   )
static func complete_quest(
    state: Dictionary,
    quest_id: String,
    approach: String
) -> Dictionary:
    var new_state = state.duplicate(true)

    # Validate quest exists and is active
    if not new_state["quests"].has(quest_id):
        push_error("Quest not found: " + quest_id)
        return state

    if new_state["quests"][quest_id]["status"] != "active":
        push_error("Quest not active: " + quest_id)
        return state

    # Load quest data
    var quest_data = DataLoader.get_quest(quest_id)
    var approach_data = quest_data["approaches"][approach]

    # Apply degradation
    for stat in approach_data["degrades"]:
        new_state["player"]["flexibility"][stat] += approach_data["degrades"][stat]
        new_state["player"]["flexibility"][stat] = clampi(
            new_state["player"]["flexibility"][stat],
            0, 10
        )

    # Apply conviction rewards
    for conviction in approach_data["rewards"]["convictions"]:
        new_state["player"]["convictions"][conviction] += approach_data["rewards"]["convictions"][conviction]

    # Set memory flags
    for flag in approach_data["rewards"]["memory_flags"]:
        var parts = flag.split("_", false, 1)
        var npc_id = parts[0]
        var flag_name = parts[1]

        if not new_state["world"]["npc_states"][npc_id]["memory_flags"].has(flag_name):
            new_state["world"]["npc_states"][npc_id]["memory_flags"].append(flag_name)

    # Mark quest complete
    new_state["quests"][quest_id]["status"] = "completed"
    new_state["quests"][quest_id]["approach_taken"] = approach

    # Unlock follow-up quests
    for outcome in quest_data["outcomes"]["all"]:
        if outcome.has("advance_to"):
            var next_quest = outcome["advance_to"]
            if DataLoader.get_quest(next_quest):
                new_state["quests"][next_quest] = {
                    "status": "available",
                    "approach_taken": "",
                    "objectives_completed": []
                }

    return new_state
```

**Key pattern elements**:

- Extends `RefCounted`, not `Node`
- Static function (no instance state)
- Takes `Dictionary`, returns new `Dictionary`
- Never mutates input (`duplicate(true)`)
- All logic is data-driven (loads quest_data)
- Error handling via early returns
- Type safety via explicit types

---

### Example: Unit Test

```gdscript
# tests/test_quest_system.gd
extends GutTest

var initial_state: Dictionary

func before_each():
    # Setup clean state for each test
    initial_state = {
        "player": {
            "flexibility": {"charisma": 10, "cunning": 10, "empathy": 10},
            "convictions": {"violence_thoughts": 0, "deceptive_acts": 0}
        },
        "world": {
            "npc_states": {
                "guard_captain": {
                    "alive": true,
                    "memory_flags": []
                }
            }
        },
        "quests": {
            "rescue_prisoner": {
                "status": "active",
                "approach_taken": "",
                "objectives_completed": []
            }
        }
    }

func test_violent_approach_degrades_charisma():
    # Act
    var result = QuestSystem.complete_quest(
        initial_state,
        "rescue_prisoner",
        "violent"
    )

    # Assert
    assert_eq(
        result["player"]["flexibility"]["charisma"],
        8,  # Started at 10, violent approach costs -2
        "Violent approach should degrade charisma by 2"
    )

func test_cannot_complete_inactive_quest():
    # Arrange
    initial_state["quests"]["rescue_prisoner"]["status"] = "completed"

    # Act
    var result = QuestSystem.complete_quest(
        initial_state,
        "rescue_prisoner",
        "violent"
    )

    # Assert - state should be unchanged
    assert_eq(
        result["quests"]["rescue_prisoner"]["status"],
        "completed",
        "Should not re-complete already completed quest"
    )
    assert_eq(
        result["player"]["flexibility"]["charisma"],
        10,
        "Stats should not change if quest not completable"
    )

func test_memory_flags_set_correctly():
    # Act
    var result = QuestSystem.complete_quest(
        initial_state,
        "rescue_prisoner",
        "violent"
    )

    # Assert
    assert_true(
        result["world"]["npc_states"]["guard_captain"]["memory_flags"].has("hostile"),
        "Violent approach should set guard_captain hostile flag"
    )

func test_state_immutability():
    # Act
    var result = QuestSystem.complete_quest(
        initial_state,
        "rescue_prisoner",
        "violent"
    )

    # Assert - original state unchanged
    assert_eq(
        initial_state["player"]["flexibility"]["charisma"],
        10,
        "Original state should not be mutated"
    )
    assert_ne(
        result,
        initial_state,
        "Should return new state object"
    )
```

**Key pattern elements**:

- Each test proves one thing
- Tests are specifications (documents expected behavior)
- Immutability is verified explicitly
- Edge cases tested (inactive quest)
- Tests are readable by non-programmers

---

### Example: Presentation Layer

```gdscript
# presentation/entities/player.gd
extends CharacterBody3D

## Player presentation - displays state, no logic

@onready var mesh: MeshInstance3D = $Mesh
@onready var health_bar: ProgressBar = $HealthBar

func _ready():
    # Subscribe to state changes
    GameState.state_changed.connect(_on_state_changed)

    # Initial render
    _on_state_changed(GameState.state)

func _on_state_changed(new_state: Dictionary):
    # Position
    global_position = new_state["player"]["position"]

    # Health bar
    health_bar.value = new_state["player"]["health"]
    health_bar.max_value = new_state["player"]["max_health"]

    # Visual feedback for degradation (color shift)
    var avg_flexibility = (
        new_state["player"]["flexibility"]["charisma"] +
        new_state["player"]["flexibility"]["cunning"] +
        new_state["player"]["flexibility"]["empathy"]
    ) / 3.0

    var material: StandardMaterial3D = mesh.get_surface_override_material(0)
    material.albedo_color = Color(
        1.0 - (avg_flexibility / 10.0),  # More red as flexibility decreases
        avg_flexibility / 10.0,           # Less green
        0.5
    )

func _physics_process(_delta):
    # Input only - no state modification
    var input_dir = Input.get_vector("move_left", "move_right", "move_up", "move_down")
    var direction = Vector3(input_dir.x, 0, input_dir.y)

    if direction:
        # Dispatch movement action to state
        GameState.dispatch(
            func(state): return PlayerSystem.move(state, direction)
        )
```

**Key pattern elements**:

- No game logic in presentation layer
- Subscribes to state changes via signal
- Only reads state, never modifies directly
- Input triggers state dispatches
- Visual feedback derives from state

---

## XIV. Final Checklist

Before considering architecture complete:

**Conceptual**:

- [ ] All patterns documented at principle level
- [ ] Logical implications of each pattern stated
- [ ] Validation criteria defined for each pattern
- [ ] Success criteria measurable and specific

**Practical**:

- [ ] AI agents can generate code from specifications
- [ ] Content creators can add quests/dialogue without programming
- [ ] Game is playable with primitives throughout development
- [ ] Architecture supports 9-month timeline

**Novel Mechanics**:

- [ ] Degradation system mechanically reinforces narrative themes
- [ ] Thoughts → Words → Actions → Character pipeline documented
- [ ] Mystery/discovery element preserved (players don't see exact numbers)
- [ ] Failsafes prevent softlocking

**Scope Control**:

- [ ] Complexity matches Gothic 2 level (not Disco Elysium)
- [ ] Linear story with reactive flavor (not branching paths)
- [ ] Combat serves narrative (not distraction)
- [ ] Content scales linearly (not exponentially)

---

**This architecture document is the contract between designer and implementation. Changes to core patterns require revision of this document. Implementation details belong in code comments, not here.**

**Version**: 1.0  
**Last Updated**: November 18, 2025  
**Next Review**: After Phase 1 completion (Month 2)

```bash
# Format - lint
source .venv/bin/activate
gdformat scripts/ &- gdlint scripts/

# Import - generate UIDs
/Applications/Godot.app/Contents/MacOS/Godot --path . -e --headless --quit-after 2000

# Run tests using gdUnit4 (smoke tests for fast iteration)
/Applications/Godot.app/Contents/MacOS/Godot --headless -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a res://test
```

Use mcp context7.com/websites/mikeschulze_github_io-gdunit4 to lookup how to use gdunit4
NEVER use GUT. ALWAYS use gdUnit4.
