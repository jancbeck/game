# Content Specification

**Purpose**: Format specifications for all game content data files
**Audience**: Content creators, AI content generators
**Note**: This is NOT for code implementation (see AGENTS.md for that)

---

## I. Quest Format

### File Location

`data/quests/[quest_id].md`

### Format Structure

```markdown
---
id: quest_identifier
act: 1
location: location_id
prerequisites:
  - completed: other_quest_id
  - npc_alive: npc_id
  - flag_set: some_flag

approaches:
  approach_name:
    label: "Text shown in UI"
    requires:
      flexibility_charisma: 5
      violence_thoughts: 3
    degrades:
      flexibility_charisma: -2
      flexibility_empathy: -1
    rewards:
      convictions:
        violence_thoughts: 2
        deceptive_acts: 1
      memory_flags:
        - npc_id_flag_name
      items:
        - item_id

outcomes:
  all:
    - advance_to: next_quest_id
    - unlock_location: location_id
    - set_flag: global_flag
---

# Quest Title

Main description text. This is what the player reads when the quest is introduced.

Can use **markdown formatting**.

## Approach: Approach Name

Description of what this approach entails. What the player will do, what risks exist, what consequences might occur.

## Approach: Other Approach

Description of the other approach.
```

---

### Field Specifications

**id** (string, required):

- Unique identifier for quest
- Format: lowercase_with_underscores
- Example: `rescue_prisoner`, `infiltrate_temple`

**act** (integer, required):

- Which act this quest belongs to
- Values: 1, 2, or 3
- Used for pacing and difficulty scaling

**location** (string, optional):

- Where quest takes place
- References location IDs from world data
- Example: `rebel_hideout`, `kings_dungeon`

**prerequisites** (array, optional):

- Conditions that must be met before quest available
- Types:
  - `completed: quest_id` - Another quest must be done
  - `npc_alive: npc_id` - NPC must not be dead
  - `flag_set: flag_name` - Global flag must be true
- Empty array = quest available from start

**approaches** (object, required):

- At least 1 approach required
- Maximum 5 approaches recommended
- Each approach is an object with:
  - `label`: UI display text (keep under 50 characters)
  - `requires`: Dictionary of stat/conviction requirements
  - `degrades`: Dictionary of stat changes (negative values)
  - `rewards`: Object containing conviction changes, memory flags, items

**outcomes** (object, required):

- `all`: Array of effects that apply regardless of approach
- Common outcomes:
  - `advance_to`: Unlock next quest
  - `unlock_location`: Make new area accessible
  - `set_flag`: Set global world flag

---

### Content Guidelines

**Quest descriptions** (markdown body):

- 100-300 words per quest
- Focus on player motivation, not mechanics
- Use active voice
- Avoid spoilers about outcomes

**Approach descriptions**:

- 50-150 words per approach
- Explain what player will do
- Hint at (don't state) consequences
- Use evocative language

**Good example**:

```
Storm the main gate. Your reputation precedes you—they'll know you're coming.
Guards will resist, blood will be shed, but you'll get inside.
```

**Bad example**:

```
This approach requires violence_thoughts >= 5 and will degrade your
charisma by -3 points. You will fight 6 guards.
```

---

### Stat Requirements Guidelines

**Flexibility requirements** (0-10 scale):

- Low barrier: 3-4
- Medium barrier: 5-7
- High barrier: 8-10

**Conviction requirements** (0-100 scale):

- Low barrier: 10-20
- Medium barrier: 30-50
- High barrier: 60-80

**Degradation amounts**:

- Light: -1
- Medium: -2 to -3
- Heavy: -4 to -5
- Never more than -5 per quest

**Conviction rewards**:

- Light: +1
- Medium: +2 to +3
- Heavy: +4 to +5

---

### Memory Flag Naming

**Format**: `npc_id_flag_name`

**Examples**:

- `guard_captain_hostile`
- `rebel_leader_trusts_player`
- `merchant_owes_favor`

**Rules**:

- NPC ID can contain underscores
- Flag name should be single word or hyphenated
- Use past tense or adjectives (not verbs)
- System parses using `rsplit("_", true, 1)`

---

### Example Complete Quest

```markdown
---
id: rescue_prisoner
act: 2
location: kings_dungeon
prerequisites:
  - completed: join_rebels

approaches:
  violent:
    label: "Fight through the guards"
    requires:
      violence_thoughts: 3
    degrades:
      flexibility_charisma: -3
      flexibility_empathy: -1
    rewards:
      convictions:
        violence_thoughts: 3
      memory_flags:
        - guard_captain_hostile
        - rebels_respect_strength

  stealthy:
    label: "Sneak through service tunnels"
    requires:
      flexibility_cunning: 6
    degrades:
      flexibility_cunning: -2
    rewards:
      convictions:
        deceptive_acts: 2
      memory_flags:
        - guard_captain_unaware
        - rebels_impressed

  diplomatic:
    label: "Bribe the warden"
    requires:
      flexibility_charisma: 7
    degrades:
      flexibility_charisma: -2
    rewards:
      convictions:
        deceptive_acts: 1
      memory_flags:
        - warden_owes_favor
      items:
        - rebels_letter

outcomes:
  all:
    - advance_to: report_to_rebel_leader
    - set_flag: prisoner_rescued
---

# Rescue the Prisoner

The rebels need you to extract a captured ally from the King's dungeons.
Time is running out—interrogators are already at work, and if they break
him, the entire rebel network could be exposed.

The dungeon is heavily guarded, but you've identified three possible approaches.
Each has its risks.

## Approach: Fight through the guards

The direct approach. Storm the gate, cut through anyone who stands in your way,
and pull your ally out by force. You'll make enemies, and the guards will
remember your face, but at least you'll get inside.

## Approach: Sneak through service tunnels

A rebel contact knows about maintenance tunnels beneath the dungeon. Precise
timing and nerves of steel required—if you're spotted underground, there's
nowhere to run.

## Approach: Bribe the warden

The warden has debts. Enough gold and a veiled threat about who might learn
of his... indiscretions. He'll look the other way, but now he owns part of you.
```

---

## II. Thought Format

### File Location

`data/thoughts/[thought_id].json`

### Format Structure

```json
{
  "id": "thought_identifier",
  "trigger": "quest_complete:quest_id:approach",
  "prompt": "Internal monologue text that sets up the choice",
  "options": [
    {
      "text": "First thought option that player can choose",
      "convictions": {
        "violence_thoughts": 2,
        "compassionate_acts": -1
      }
    },
    {
      "text": "Second thought option",
      "convictions": {
        "violence_thoughts": 1
      }
    },
    {
      "text": "Third thought option",
      "convictions": {
        "compassionate_acts": 1,
        "violence_thoughts": -1
      }
    }
  ]
}
```

---

### Field Specifications

**id** (string, required):

- Unique identifier for thought
- Format: lowercase_with_underscores
- Example: `after_violent_quest`, `before_betrayal`

**trigger** (string, required):

- When thought should appear
- Format: `event_type:event_id:optional_detail`
- Event types:
  - `quest_complete:quest_id:approach` - After specific quest/approach
  - `act_start:1` - At beginning of act
  - `story_beat:beat_name` - At specific story moment

**prompt** (string, required):

- Internal monologue text
- 50-200 characters
- First person, present tense
- Sets up the choice without biasing

**options** (array, required):

- 2-4 options recommended
- Each option has:
  - `text`: What player thinks (100-200 chars)
  - `convictions`: Dictionary of conviction changes

---

### Content Guidelines

**Prompt text**:

- Present as question or observation
- No "correct" framing
- Ambiguous moral stance
- Player's voice, not narrator

**Good prompts**:

```
"That was necessary. Wasn't it?"
"I'm becoming something. But what?"
"The blood on my hands—does it wash off?"
```

**Bad prompts**:

```
"You just did a bad thing. How do you feel?"
"Choose whether you're good or evil."
"This choice will affect your stats."
```

**Option text**:

- Each option is a complete thought
- Distinct philosophical positions
- None obviously "correct"
- Varying lengths okay (50-200 chars)

**Good options**:

```
"He deserved it. The world is better without him."
"I did what I had to. I don't enjoy this."
"There had to be another way. I'm becoming something I hate."
```

**Bad options**:

```
"I'm evil now."
"I feel bad."
"Violence is sometimes necessary."
```

---

### Conviction Changes

**Amounts**:

- Small shift: ±1
- Medium shift: ±2 to ±3
- Large shift: ±4 to ±5

**Direction**:

- Positive values increase conviction
- Negative values decrease conviction
- Zero is valid (no change to that conviction)

**Balance**:

- Most options should affect 1-2 convictions
- Avoid options that only increase (no tradeoff)
- Consider opposing convictions (violence vs compassion)

**Good balance**:

```json
{
  "text": "He deserved it.",
  "convictions": {
    "violence_thoughts": 3,
    "compassionate_acts": -2
  }
}
```

**Bad balance**:

```json
{
  "text": "I'm a good person.",
  "convictions": {
    "compassionate_acts": 5
  }
}
```

---

### Example Complete Thought

```json
{
  "id": "after_rescue_violent",
  "trigger": "quest_complete:rescue_prisoner:violent",
  "prompt": "The guards are dead. Your ally is free. But the blood won't wash off your sword.",
  "options": [
    {
      "text": "They chose to stand in my way. Their deaths are on them, not me.",
      "convictions": {
        "violence_thoughts": 3,
        "compassionate_acts": -2
      }
    },
    {
      "text": "I did what I had to. The alternative was worse. I think.",
      "convictions": {
        "violence_thoughts": 1,
        "compassionate_acts": -1
      }
    },
    {
      "text": "There had to be another way. I'm losing myself to this.",
      "convictions": {
        "compassionate_acts": 2,
        "violence_thoughts": -1
      }
    }
  ]
}
```

---

## III. Dialogue Format (Future - Phase 3)

### File Location

`data/dialogues/[npc_id]_[scene].yarn`

### Format Structure

```yarn
title: NPC_SceneName
tags: main_story, act1, npc_name
---
<<if visited("NPC_SceneName")>>
  NPC: We've spoken before.
  -> AlreadyMet
<<endif>>

<<if $world.npc_states.guard_captain.memory_flags contains "hostile">>
  NPC: You! Guards!
  -> HostileEncounter
<<endif>>

NPC: Opening dialogue line.

Player: Context for what we're discussing.

[[Polite response|PoliteChoice]] <<if $player.flexibility.charisma >= 5>>
[[Aggressive response|AggressiveChoice]] <<if $player.convictions.violence_thoughts >= 3>>
[[Leave|Exit]]

===
title: PoliteChoice
---
<<set $player.flexibility.charisma -= 1>>

Player: Polite dialogue.
NPC: Response to politeness.

-> NextNode

===
title: AggressiveChoice
---
<<set $player.convictions.violence_thoughts += 1>>
<<set $world.npc_states.npc_id.memory_flags += "player_was_rude">>

Player: Aggressive dialogue.
NPC: Negative response.

-> CombatOrConsequence
```

---

### Yarn Conventions

**Conditionals**:

- Use `<<if condition>>` for branching
- Common conditions:
  - `visited("NodeName")` - Has player seen this node?
  - `$player.flexibility.stat >= value` - Stat check
  - `$player.convictions.conviction >= value` - Conviction check
  - `$world.npc_states.npc_id.memory_flags contains "flag"` - Memory check

**State Changes**:

- Use `<<set variable += value>>` for incrementing
- Use `<<set variable -= value>>` for decrementing
- Always modify through state paths

**Choice Format**:

- `[[Display Text|NodeName]]` for unconditional choice
- `[[Display Text|NodeName]] <<if condition>>` for gated choice
- Always have at least one ungated exit option

---

### Content Guidelines

**Dialogue density**:

- 200-400 words per major conversation
- 50-100 words per minor interaction
- Break long conversations into nodes

**Choice presentation**:

- 2-4 choices per node
- At least 1 choice always available
- Gated choices show requirements on hover

**NPC voice**:

- Each NPC has distinct speech pattern
- Consistent personality across scenes
- React to player's reputation/choices

---

## IV. Character Format (Future - Phase 2)

### File Location

`data/characters/[npc_id].json`

### Format Structure

```json
{
  "id": "npc_identifier",
  "name": "Display Name",
  "faction": "faction_id",
  "initial_state": {
    "alive": true,
    "relationship": 0,
    "memory_flags": []
  },
  "dialogue_variants": {
    "greeting": {
      "default": "npc_neutral_greeting",
      "if_flags": {
        "player_helped": "npc_friendly_greeting",
        "player_betrayed": "npc_hostile_greeting"
      }
    },
    "quest_giver": {
      "default": "npc_quest_intro",
      "if_flags": {
        "quest_completed": "npc_quest_thanks"
      }
    }
  },
  "combat_stats": {
    "health": 150,
    "damage": 25,
    "abilities": ["ability_id1", "ability_id2"]
  },
  "appearance": {
    "primitive": "cube",
    "color": "#FF5733",
    "size": 1.0
  }
}
```

---

### Field Specifications

**id** (string, required):

- Unique identifier
- Used in memory flags, dialogue references
- Example: `rebel_leader`, `guard_captain`

**name** (string, required):

- Display name shown to player
- Example: "Captain Marcus", "The High Priest"

**faction** (string, optional):

- Which faction NPC belongs to
- Values: `rebels`, `clerics`, `kings_guard`, `neutral`

**initial_state** (object, required):

- Starting conditions
- `alive`: Always true initially
- `relationship`: -100 to 100, starts at 0
- `memory_flags`: Empty array initially

**dialogue_variants** (object, required):

- Maps scene types to dialogue nodes
- `default`: Fallback if no flags match
- `if_flags`: Dictionary of flag → dialogue node

**combat_stats** (object, optional):

- Only if NPC can be fought
- `health`: HP value
- `damage`: Base damage
- `abilities`: Array of ability IDs

**appearance** (object, required):

- Placeholder visual representation
- `primitive`: "cube", "sphere", "capsule"
- `color`: Hex color code
- `size`: Scale multiplier (1.0 = default)

---

## V. Item Format (Future - Phase 3)

### File Location

`data/items/[item_id].json`

### Format Structure

```json
{
  "id": "item_identifier",
  "name": "Display Name",
  "type": "weapon",
  "slot": "main_hand",
  "description": "Item description text shown in inventory.",
  "stats": {
    "damage": 25,
    "speed": 1.2
  },
  "requirements": {
    "flexibility_cunning": 5,
    "violence_thoughts": 10
  },
  "value": 150,
  "appearance": {
    "primitive": "cylinder",
    "color": "#C0C0C0"
  }
}
```

---

### Field Specifications

**type** (string, required):

- Values: `weapon`, `armor`, `consumable`, `quest_item`, `misc`

**slot** (string, conditional):

- Required if type is `weapon` or `armor`
- Weapon slots: `main_hand`, `off_hand`, `two_hand`
- Armor slots: `head`, `chest`, `legs`, `hands`, `feet`

**requirements** (object, optional):

- Stats/convictions needed to use item
- Can require flexibility or convictions
- Empty object = no requirements

**value** (integer, required):

- Gold value
- Used for shops, rewards
- 0 = priceless/quest item

---

## VI. World Data Format (Future - Phase 2)

### File Location

`data/world/locations.json`

### Format Structure

```json
{
  "locations": [
    {
      "id": "location_identifier",
      "name": "Display Name",
      "description": "Location description text.",
      "act": 1,
      "accessible": true,
      "scene": "res://scenes/locations/location.tscn",
      "connections": ["other_location_id"],
      "npcs": ["npc_id1", "npc_id2"],
      "quests": ["quest_id1"]
    }
  ],
  "global_flags": [
    {
      "id": "flag_name",
      "description": "What this flag represents",
      "initial_value": false
    }
  ]
}
```

---

## VII. Content Generation Prompts

### For AI Content Generators

**Quest Generation Prompt Template**:

```
Generate a quest in Gothic-inspired degradation RPG format.

Context:
- Act: [1/2/3]
- Player has joined: [faction]
- Previous quest: [quest_id]
- Theme: [brief theme description]

Requirements:
1. Quest should take 10-15 minutes
2. Include 3 approaches: violent, cunning, diplomatic
3. Each approach requires different stats
4. Degradation should total -3 to -5 flexibility points
5. Include memory flags that affect NPC reactions
6. Outcome advances to next story beat

Output format: Markdown with YAML frontmatter (see CONTENT_SPEC.md Section I)
```

**Thought Generation Prompt Template**:

```
Generate an internal monologue scene for degradation RPG.

Context:
- Triggers after: [quest_id] with [approach] approach
- Player's recent choices: [list of approaches]
- Theme: [moral dilemma or self-reflection theme]

Requirements:
1. Prompt should be 50-150 characters
2. Include 3 thought options
3. Options represent different philosophical stances
4. No option is obviously "correct"
5. Conviction changes should total +3 to +5
6. Consider opposing convictions (violence vs compassion)

Output format: JSON (see CONTENT_SPEC.md Section II)
```

**Dialogue Generation Prompt Template**:

```
Generate NPC dialogue in Yarn format.

Context:
- NPC: [npc_id] ([personality traits])
- Scene: [what's happening]
- Player's reputation: [memory flags]
- Available stats: charisma [X], violence [Y]

Requirements:
1. 200-400 words total
2. Include 3-4 player response options
3. At least 1 option always available
4. Gate options by stats/convictions
5. Include consequences (stat changes, memory flags)
6. Branch based on memory flags

Output format: Yarn (see CONTENT_SPEC.md Section III)
```

---

## VIII. Quality Checklist

### Before Submitting Quest Content

- [ ] Quest ID is unique and lowercase_with_underscores
- [ ] At least 1 approach defined, maximum 5
- [ ] Each approach has label, requirements, degrades, rewards
- [ ] Total degradation is -3 to -5 flexibility points per quest
- [ ] Outcomes include at least advance_to or unlock_location
- [ ] Memory flags follow npc_id_flag_name format
- [ ] Description is 100-300 words
- [ ] Each approach described in 50-150 words
- [ ] No spoilers about exact stat changes in text
- [ ] Markdown formatting is valid

---

### Before Submitting Thought Content

- [ ] Thought ID is unique and lowercase_with_underscores
- [ ] Trigger format is correct (event_type:id:detail)
- [ ] Prompt is 50-200 characters
- [ ] Prompt is ambiguous (no "correct" stance)
- [ ] 2-4 options included
- [ ] Each option is 50-200 characters
- [ ] Each option is distinct philosophical position
- [ ] Conviction changes are ±1 to ±5
- [ ] At least one option affects multiple convictions
- [ ] Total conviction changes are +3 to +5
- [ ] JSON is valid

---

### Before Submitting Dialogue Content

- [ ] Yarn syntax is valid
- [ ] Node names are unique
- [ ] Conditionals use correct state paths
- [ ] At least 1 choice always available (ungated)
- [ ] Stat changes use correct syntax (<<set>>)
- [ ] Memory flags use correct format
- [ ] Conversation is 200-400 words
- [ ] NPC voice is consistent
- [ ] Player choices are meaningful
- [ ] Dead ends avoided (always leads somewhere)

---

## IX. Style Guide

### Tone Guidelines

**Overall game tone**:

- Dark fantasy (Gothic 2 inspiration)
- Morally ambiguous
- Character-driven
- Introspective without being pretentious

**Writing style**:

- Active voice preferred
- Present tense for immediate actions
- Past tense for backstory
- Second person for internal monologue ("You think...")
- Third person for narration

**Avoid**:

- Modern slang or anachronisms
- Breaking fourth wall
- Explicit stat/mechanic references in narrative
- Overly flowery prose
- Meme references or jokes

---

### Word Choice

**Preferred terms**:

- "Ally" over "friend"
- "Conflict" over "fight"
- "Consequence" over "result"
- "Choice" over "decision"

**Faction-specific language**:

- Rebels: Direct, passionate, idealistic
- Clerics: Formal, dogmatic, euphemistic
- King's Guard: Military, hierarchical, duty-focused
- Neutral NPCs: Pragmatic, cautious, self-interested

---

### Common Mistakes to Avoid

**Quest content**:

- ❌ "This quest requires 5 charisma"
- ✅ "Convincing the guard will require charm"

**Thought content**:

- ❌ "Choose whether you're good or evil"
- ✅ "Was that justice, or just revenge?"

**Dialogue**:

- ❌ "Your violence_thoughts stat is too low"
- ✅ "[This option requires a history of violence]" (grey text)

**Descriptions**:

- ❌ "Press E to interact"
- ✅ "The guard eyes you suspiciously"

---

## X. Testing Your Content

### Manual Testing Checklist

**For quests**:

1. Can quest be started? (prerequisites met)
2. Does each approach work? (try all)
3. Do stats degrade correctly? (check debug UI)
4. Do memory flags set? (check NPC reactions)
5. Does next quest unlock? (verify chain)

**For thoughts**:

1. Does thought trigger at right time?
2. Do all options work? (try each)
3. Do convictions change? (check debug UI)
4. Can thought be skipped? (shouldn't be possible)

**For dialogues**:

1. Does correct greeting play? (based on flags)
2. Are gated options properly hidden?
3. Do choices have consequences?
4. Can conversation be exited gracefully?

---

### Validation Tools

**Quest validation**:

- Run through DataLoader.get_quest(quest_id)
- Should return complete Dictionary
- No errors in console

**Thought validation**:

- Run through ThoughtSystem.get_thought_data(thought_id)
- Should return complete Dictionary
- No errors in console

**Dialogue validation**:

- (Phase 3) Yarn linter/validator
- Check for unreachable nodes
- Check for infinite loops

---

## XI. Localization Considerations

### Preparing for Translation

**Quest files**:

- Keep YAML frontmatter in English (not translated)
- Translate only markdown body
- Translate approach labels and descriptions

**Thought files**:

- Translate prompt and all option text
- Keep JSON structure and conviction keys in English

**Dialogue files**:

- Translate all dialogue text
- Keep node names, tags, and variable names in English

**Character files**:

- Translate name and description
- Keep id, faction, and flags in English

---

### String Length Considerations

**Be aware that translations expand/contract**:

- German: +20-30% length
- French: +15-20% length
- Japanese: -10-20% length
- Spanish: +15-25% length

**Design with flexibility**:

- UI should accommodate 30% longer text
- Don't hardcode text wrapping
- Test with longest likely translation

---

## XII. Version Control

### Content Versioning

**When to update**:

- Major content changes: Increment version (1.0 → 2.0)
- Minor text edits: Increment decimal (1.0 → 1.1)
- Typo fixes: Increment patch (1.0.1 → 1.0.2)

**Track in file**:

```yaml
---
id: quest_id
version: 1.2
last_updated: 2025-11-19
---
```

---

### Change Log

**Document changes**:

```markdown
## Quest: rescue_prisoner

### Version 1.2 (2025-11-19)

- Reduced charisma requirement for diplomatic approach (7→6)
- Added memory flag: warden_owes_favor
- Clarified stealthy approach description

### Version 1.1 (2025-11-15)

- Fixed typo in diplomatic approach text
- Adjusted degradation values for balance

### Version 1.0 (2025-11-10)

- Initial implementation
```

---

## XIII. Quick Reference

### Common Data Paths

```
Quest: data/quests/[quest_id].md
Thought: data/thoughts/[thought_id].json
Dialogue: data/dialogues/[npc_id]_[scene].yarn
Character: data/characters/[npc_id].json
Item: data/items/[item_id].json
World: data/world/locations.json
```

### Naming Conventions

```
Quest IDs: rescue_prisoner, infiltrate_temple
Thought IDs: after_violent_quest, before_betrayal
NPC IDs: rebel_leader, guard_captain
Memory Flags: npc_id_flag_name
Item IDs: iron_sword, health_potion
Location IDs: rebel_hideout, kings_dungeon
```

### Stat Ranges

```
Flexibility: 0-10 (starts 10, decreases)
Convictions: 0-100 (starts 0, increases)
Relationship: -100 to 100 (starts 0)
Health: varies by character
```
