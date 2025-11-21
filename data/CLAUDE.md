# Content Creation Guide

## Quest Format

### Location: `/data/quests/[quest_id].json`

```json
{
  "id": "join_rebels",
  "act": 1,
  "location": "rebel_camp",
  "prerequisites": [],
  "approaches": {
    "diplomatic": {
      "label": "Offer your services",
      "requires": {
        "flexibility_charisma": 5
      },
      "degrades": {
        "flexibility_charisma": -5,
        "flexibility_empathy": -2
      },
      "rewards": {
        "convictions": {
          "violence_thoughts": -1
        },
        "memory_flags": ["rebel_leader_trusts_player"]
      }
    },
    "violent": {
      "label": "Threaten them",
      "requires": {
        "violence_thoughts": 3
      },
      "degrades": {
        "flexibility_charisma": -8
      },
      "rewards": {
        "convictions": {
          "violence_thoughts": 2
        },
        "memory_flags": ["rebel_leader_fears_player"]
      }
    }
  },
  "outcomes": {
    "all": [{ "advance_to": "rescue_prisoner" }]
  },
  "summary": "You found the camp. To earn their trust, you must offer something."
}
```

### Key Rules:

- **id**: Unique, `lowercase_with_underscores`
- **prerequisites**: Use only `{"completed": "quest_id"}` pattern
- **approaches**: At least 1, max ~5. One must always be available
- **requires**: Use existing stats only (flexibility\__, _\_thoughts)
- **degrades**: Usually negative flexibility values
- **rewards**: Convictions (positive) and memory_flags
- **memory_flags**: Format `npc_id_flag_name`

## Dialogic Integration

### Timeline Naming Convention

- Quests: `quest_[id]_intro`, `quest_[id]_resolution`
- NPCs: `npc_[name]_[topic]`
- Thoughts: `thought_[context]_[variant]`

### Hybrid Timeline Syntax

**Use `[signal arg="..."]` for state mutations** (changes to game state):

```
[signal arg="start_quest:join_rebels"]
[signal arg="complete_quest:join_rebels:diplomatic"]
[signal arg="modify_conviction:violence_thoughts:2"]
[signal arg="modify_flexibility:charisma:-3"]
```

**Use `do GameStateActions.*` for queries** (read-only checks):

```
do GameStateActions.can_start_quest("quest_id")
do GameStateActions.get_flexibility("charisma")
do GameStateActions.get_conviction("violence_thoughts")
do GameStateActions.has_memory_flag("npc_id", "flag_name")
```

**Why This Matters**:

- **Signals**: Logged by DialogSystem, maintain clean architecture flow
- **`do` statements**: Direct method calls for conditions, safe because they never mutate state
- **Debugging**: Signals appear in logs, queries are silent
- **Content creation**: Use signals when changing the world, use `do` when checking the world

**Rules**:

- Quest/approach IDs must exist in JSON
- Stat names must match GameState keys exactly
- No new signal types without PM approval
- Always have at least one ungated option (desperate choice)

### Gating Choices (Examples)

**Flexibility check**:
```
- [Diplomatic] Negotiate | [if GameStateActions.get_flexibility("charisma") >= 5]
  [signal arg="complete_quest:rescue_prisoner:diplomatic"]
```

**Conviction check**:
```
- [Violent] Attack | [if GameStateActions.get_conviction("violence_thoughts") >= 3]
  [signal arg="complete_quest:rescue_prisoner:violent"]
```

**Quest prerequisite**:
```
- Ask about the ruins | [if GameStateActions.can_start_quest("investigate_ruins")]
  [signal arg="start_quest:investigate_ruins"]
```

**Memory flag check**:
```
- Remind them of your promise | [if GameStateActions.has_memory_flag("rebel_leader", "trusts_player")]
  They remember. Trust is currency here.
```

## Existing Stats Reference

### Flexibility (0-10, starts at 10)

- `flexibility_charisma` - Social influence
- `flexibility_cunning` - Clever solutions
- `flexibility_empathy` - Understanding others

### Convictions (0+, starts at 0, no max)

- `violence_thoughts` - Tendency toward force
- `deceptive_acts` - Manipulation tendency
- `compassionate_acts` - Kindness accumulation
- `duty_above_all` - Loyalty to order
- `question_authority` - Rebellious thinking

## Tone Guidelines

### Gothic Elements

- Moral ambiguity (no clear heroes/villains)
- Physical and mental decay
- Religious/philosophical undertones
- Oppressive atmosphere
- Consequences that compound

### Disco Elysium Inspiration

- Internal dialogue as character development
- Thoughts that reshape perception
- Mundane conversations reveal profound truths
- Failure as narrative opportunity
- Political philosophy without preaching

### Writing Style

- Concise but evocative
- Show degradation through changed options
- Let mechanics tell story (lost abilities)
- NPCs react to invisible stats
- Player discovers transformation, doesn't plan it

### Characters: `/data/characters/[npc_id].json`

```json
{
  "id": "rebel_leader",
  "name": "Elira",
  "faction": "rebels",
  "initial_state": {
    "alive": true,
    "relationship": 0,
    "memory_flags": []
  }
}
```

### Items: `/data/items/[item_id].json`

```json
{
  "id": "iron_sword",
  "type": "weapon",
  "requirements": {
    "violence_thoughts": 10
  }
}
```

## Quick Reference

### Common Memory Flags

- `[npc]_trusts_player`
- `[npc]_fears_player`
- `[npc]_dead`
- `quest_[id]_[outcome]`
- `location_[id]_discovered`

### Quest Prerequisites

- `{"completed": "quest_id"}`
- Empty array `[]` for always available

### Standard Approaches

- `violent` - Force/intimidation
- `diplomatic` - Negotiation/charm
- `cunning` - Deception/cleverness
- `empathetic` - Understanding/kindness
- `desperate` - Last resort (no requirements)

## Story Outline (Act 1-3)

**Act 1: The Descent (Introduction to Degradation)**
**Quest A: `join_rebels`** (Implemented) - Player chooses a faction (Rebels) out of necessity.
**Quest B: `rescue_prisoner`** (Implemented) - First moral compromise; violence vs stealth.
**Quest C: `investigate_ruins`** (Next) - Discovery of the Corruption; first major sacrifice (health/sanity).
**Quest D: `secure_camp_defenses`** - The camp is attacked; player must choose who to save (pragmatism vs heroism).
**Quest E: `confront_the_traitor`** - A friend betrays the camp; justice vs mercy vs utility.

**Act 2: The Funnel (Narrowing Options)**
**Quest F: `seek_the_oracle`** - Journey to a dangerous location; requires high conviction to survive.
**Quest G: `retrieve_cursed_artifact`** - The only weapon that can help; holding it degrades you constantly.
**Quest H: `betray_faction_trust`** - A necessary evil to gain power; alienates early allies.
**Quest I: `the_great_sacrifice`** - A ritual requiring a permanent stat loss (e.g., permanently -10 Max Health or -5 Charisma).
**Quest J: `defend_the_breach`** - A siege scenario; your previous choices determine who shows up to help.

**Act 3: The Consequence (You Are What You Made)**
**Quest K: `assault_the_spire`** - The final push; options are heavily gated by previous degradation.
**Quest L: `face_the_shadow`** - Confronting the antagonist who is a mirror of your degradation.
**Quest M: `the_final_choice`** - Determine the fate of the world based on your dominant Conviction.
**Epilogue** - Narrative summary of your character's final state.
