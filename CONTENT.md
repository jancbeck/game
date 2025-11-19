# CONTENT.md – Content Author Agent Guide

This document defines how the **Content Author agent** creates and maintains narrative and systemic content for the Gothic-inspired degradation RPG.

You do **not**:
- Change engine code or architecture
- Invent new data formats or GameState fields
- Modify Dialogic integration logic

You **do**:
- Create and edit **quest JSON** data
- Create and edit **Dialogic 2 timelines** (quests, NPCs, thoughts)
- Use existing systems (quests, convictions, flexibility, memory flags) correctly
- Maintain tone and narrative consistency

---

## I. Quest Format

### File Location

`data/quests/[quest_id].json`
Example: `data/quests/join_rebels.json`

### Format Structure

```json
{
  "id": "join_rebels",
  "act": 1,
  "location": "rebel_camp",
  "prerequisites": [],
  "approaches": {
    "diplomatic": {
      "label": "Offer your services",
      "requires": {},
      "degrades": {
        "flexibility_charisma": -5,
        "flexibility_empathy": -2
      },
      "rewards": {
        "memory_flags": ["rebel_leader_trusts_player"]
      }
    }
  },
  "outcomes": {
    "all": [
      { "advance_to": "rescue_prisoner" }
    ]
  },
  "summary": "You found the camp. To earn their trust, you must offer something they cannot refuse."
}
```

### Field Specifications

-   **id** (string, required)
    -   Unique quest identifier
    -   Format: `lowercase_with_underscores`
    -   Example: `join_rebels`, `rescue_prisoner`

-   **act** (integer, required)
    -   Story act this quest belongs to
    -   Used for pacing and internal organization

-   **location** (string, optional)
    -   Logical location key where the quest is centered
    -   Example: `rebel_camp`, `kings_dungeon`

-   **prerequisites** (array, optional)
    -   Conditions that must be satisfied before the quest is available
    -   Current pattern:
        -   `{ "completed": "other_quest_id" }` – quest must be completed
    -   Leave empty (`[]`) if always available
    -   Do not invent new prerequisite types without Architect approval

-   **approaches** (object, required)
    -   Keys are approach IDs, values are approach definitions
    -   At least 1 approach, at most ~5

    Each approach:
    ```json
    "approach_id": {
      "label": "UI label / base choice text",
      "requires": {
        "flexibility_charisma": 5
      },
      "degrades": {
        "flexibility_charisma": -2,
        "flexibility_empathy": -1
      },
      "rewards": {
        "memory_flags": ["rebel_leader_trusts_player"]
      }
    }
    ```
    -   **label** (string): Short text for UI/choice base. Dialogic can restyle it, but semantics should match.
    -   **requires** (object): Stat/conviction requirements to use this approach (keys must match existing stats). Keep to existing keys like `flexibility_charisma`, `flexibility_cunning`, `violence_thoughts`, etc.
    -   **degrades** (object): Stat changes applied on completion (usually negative flexibility).
        -   Keys: existing flexibility stats
        -   Values: negative numbers
        -   Never more than about -5 to a single stat from one quest
    -   **rewards** (object): Systemic rewards. Current safe field:
        -   `memory_flags`: `string[]` – flags that mark persistent outcomes
        -   Format: `npc_id_flag_name` (see “Memory Flag Naming” below)

-   **outcomes** (object, required)
    ```json
    "outcomes": {
      "all": [
        { "advance_to": "rescue_prisoner" }
      ]
    }
    ```
    -   **all** (array): Effects that always apply when the quest completes. Current patterns:
        -   `{ "advance_to": "other_quest_id" }` – unlock next quest in chain
        -   Do not add new outcome types without Architect approval

-   **summary** (string, required)
    -   Short description for journals/UI
    -   1–3 sentences describing the situation and dilemma
    -   No explicit mention of numeric stats or mechanics

---

## II. Thought Content (Dialogic)

Thoughts are implemented as Dialogic timelines, not separate JSON files.

Typical pattern:
-   A quest trigger or other system starts a thought timeline:
    -   Example ID: `thought_before_join_rebels`
-   The timeline:
    -   Shows a short internal monologue prompt
    -   Offers 2–4 options (choices)
    -   Each option emits signals like `modify_conviction` / `modify_flexibility`
    -   After the thought resolves, the quest’s main dialogue continues

### Naming

-   Use `thought_<context>_<variant>`
Examples:
-   `thought_before_join_rebels`
-   `thought_after_rescue_prisoner_01`

### Structure (conceptual)

Inside Dialogic editor:
-   First node: prompt (internal monologue)
-   Next nodes: options as choices
-   Each choice:
    -   Text = a distinct thought / stance
    -   Emits one or more signals via Dialogic’s event system, e.g.:
        -   `modify_conviction:violence_thoughts:2`
        -   `modify_flexibility:charisma:-2`

You do not implement the signal parsing logic; you only use the agreed signal patterns.

---

## III. Dialogue Content (Dialogic)

All in-game conversations (NPC talk, quest intros/resolutions, thoughts) are Dialogic timelines.

### Timeline IDs

Use clear, consistent IDs:
-   **Quests**:
    -   `quest_<id>_intro` – e.g. `quest_join_rebels_intro`
    -   `quest_<id>_resolution`
-   **NPC conversations**:
    -   `npc_<name>_<topic>` – e.g. `npc_guard_captain_intro`
-   **Thoughts**:
    -   `thought_<context>_<variant>`

### Characters (Dialogic feature)

Use Dialogic Characters (resources) rather than hard-coded names:
-   Each speaking actor should have:
    -   Character ID (e.g. `rebel_leader`, `guard_captain`)
    -   Display name
    -   Color / portrait config as supported by Dialogic
-   Timelines should reference these characters where available, so:
    -   Visual look and feel can be changed centrally
    -   Voice consistency is easier to maintain

When new important NPCs appear, ensure a Character resource exists or request one via PM/Architect if needed.

### Signals and GameStateActions

Dialogic timelines never modify GameState directly. Instead, they emit signals parsed by DialogSystem and forwarded to GameStateActions.

Standard signal forms:
-   `start_quest:<quest_id>`
-   `complete_quest:<quest_id>:<approach_id>`
-   `modify_conviction:<name>:<delta>`
-   `modify_flexibility:<name>:<delta>`

Examples:
-   `start_quest:join_rebels`
-   `complete_quest:join_rebels:diplomatic`
-   `modify_conviction:violence_thoughts:2`
-   `modify_flexibility:charisma:-3`

Rules:
-   Quest IDs must exist in quest JSON.
-   Conviction/flexibility names must match GameState’s keys.
-   Do not invent new signal verbs; ask PM/Architect if new behaviours are needed.

### Gating

Gated choices/branches should use whatever condition hooks the coding team exposes (e.g. functions that check `GameStateActions.can_start_quest("quest_id")` or memory flags).

Principles:
-   At least one choice should always be available (never lock the player in total silence).
-   Gated choices should communicate requirements via text (e.g. greyed-out + hint).

---

## IV. Character Format (Future – Phase 2)

Planned, not fully implemented yet. Do not add characters without PM/Architect alignment.

### File Location

`data/characters/[npc_id].json`

### Format Structure

```json
{
  "id": "rebel_leader",
  "name": "Elira",
  "faction": "rebels",
  "initial_state": {
    "alive": true,
    "relationship": 0,
    "memory_flags": []
  },
  "dialogue_variants": {
    "greeting": {
      "default": "npc_rebel_leader_greeting_neutral",
      "if_flags": {
        "rebel_leader_trusts_player": "npc_rebel_leader_greeting_friendly"
      }
    }
  },
  "combat_stats": {
    "health": 150,
    "damage": 25,
    "abilities": ["cleave", "rally_allies"]
  },
  "appearance": {
    "primitive": "cube",
    "color": "#FF5733",
    "size": 1.0
  }
}
```

### Field Highlights

-   **id** – unique ID, matches references elsewhere (memory flags, Dialogic character)
-   **name** – display name
-   **faction** – e.g. `rebels`, `clerics`, `kings_guard`, `neutral`
-   **dialogue_variants** – mapping from situations to Dialogic timeline IDs
-   **appearance** – placeholder 3D representation for prototype

Treat this section as a future spec; follow it only when the PM/Architect explicitly assigns character data tasks.

---

## V. Item Format (Future – Phase 3)

Also future-facing.

### File Location

`data/items/[item_id].json`

```json
{
  "id": "iron_sword",
  "name": "Iron Sword",
  "type": "weapon",
  "slot": "main_hand",
  "description": "A sturdy but unremarkable iron sword.",
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

Follow the given field guidelines once item content becomes active work.

---

## VI. World Data Format (Future – Phase 2)

### File Location

`data/world/locations.json`

```json
{
  "locations": [
    {
      "id": "rebel_camp",
      "name": "Rebel Camp",
      "description": "A hidden outpost deep in the forest.",
      "act": 1,
      "accessible": true,
      "scene": "res://scenes/locations/rebel_camp.tscn",
      "connections": ["forest_path"],
      "npcs": ["rebel_leader"],
      "quests": ["join_rebels"]
    }
  ],
  "global_flags": [
    {
      "id": "prisoner_rescued",
      "description": "The rebel prisoner was rescued from the dungeon.",
      "initial_value": false
    }
  ]
}


⸻
## VIII. Quality Checklist

### Before Submitting Quest Content (JSON)
*   Quest ID is unique and `lowercase_with_underscores`
*   File is placed under `data/quests/[quest_id].json`
*   JSON is valid (no trailing commas, correct quoting)
*   At least 1 approach defined, maximum 5
*   Each approach has `label`, `requires`, `degrades`, `rewards`
*   Degrades are negative flexibility changes (per quest total ≈ -3 to -5 across all degrades)
*   Outcomes include at least one effect (e.g. `advance_to`)
*   Memory flags follow `npc_id_flag_name` format
*   `summary` is present and 30–80 words (1–3 sentences)
*   No explicit numeric stat values mentioned in summary
*   All quest and approach IDs referenced in Dialogic timelines are consistent

---

### Before Submitting Thought Content (Dialogic Timelines)
*   Thought timeline ID is unique and `thought_<context>_<variant>`
*   Timeline is saved and appears correctly in the Dialogic editor
*   Prompt (first line/section) is ~50–200 characters
*   Prompt expresses an ambiguous internal state; no obvious “correct” moral stance
*   2–4 player options are present
*   Each option’s text is ~50–200 characters
*   Each option represents a distinct philosophical / emotional position
*   Each option emits one or more `modify_conviction` / `modify_flexibility` signals
*   Conviction deltas per option are between ±1 and ±5
*   At least one option affects multiple convictions (trade-offs)
*   Combined effect of all options (if taken over time) keeps conviction values within reasonable bounds (no extreme stat explosions)

---

### Before Submitting Dialogue Content (Dialogic Timelines)
*   Dialogic timeline loads without errors in editor
*   Timeline ID follows naming convention (`quest_`, `npc_`, `thought_`, etc.)
*   All node names / labels are unique where required by Dialogic
*   Conditionals use only supported variables/flags (no ad-hoc state)
*   At least one choice is always available (ungated path forward)
*   Stat/memory changes are implemented via signals (e.g. `modify_*`, `start_quest`, `complete_quest`)
*   Memory flags used match the `npc_id_flag_name` pattern
*   Conversation length appropriate:
    *   Major conversations: ~200–400 words total
    *   Minor interactions: ~50–150 words
*   NPC voice is consistent with faction and previous appearances
*   Player choices are meaningful and reflect different attitudes or strategies
*   No dead-ends: all paths lead to a sensible continuation or termination state

---

## IX. Style Guide

### Tone Guidelines

**Overall tone:**
*   Dark fantasy (Gothic 2 inspiration)
*   Morally ambiguous and grounded
*   Character-driven and consequence-aware
*   Introspective without being pretentious or verbose

**Writing style:**
*   Prefer active voice
*   Present tense for immediate actions and dialogue
*   Past tense for backstory or recalled events
*   Second person for internal monologue ("You think...")
*   Third person for narration where needed ("The guard watches you.")

**Avoid:**
*   Modern slang or obvious anachronisms
*   Breaking the fourth wall
*   Explicit stat or mechanic references in narrative text
*   Overly flowery, purple prose
*   Meme references or out-of-world jokes

---

### Word Choice

**Preferred terms:**
*   Use “ally” over “friend”
*   Use “conflict” over “fight” when talking broadly
*   Use “consequence” over “result”
*   Use “choice” over “decision” in UI-facing text

**Faction-specific language:**
*   Rebels: direct, passionate, idealistic, sometimes reckless
*   Clerics: formal, dogmatic, euphemistic about violence
*   King’s Guard: militarised, hierarchical, duty-focused
*   Neutral NPCs: pragmatic, cautious, self-interested

---

### Common Mistakes to Avoid

**Quest content:**
*   ❌ “This quest requires 5 charisma.”
*   ✅ “You’ll need charm and presence to sway the captain.”

**Thought content:**
*   ❌ “Choose whether you’re good or evil.”
*   ✅ “Was that justice, or just revenge?”

**Dialogue:**
*   ❌ “Your violence_thoughts stat is too low.”
*   ✅ “[You haven’t spilled enough blood to convince him.]” (implied in flavour text)

**Descriptions:**
*   ❌ “Press E to interact.”
*   ✅ “The guard eyes you, waiting to see what you’ll do.”

---

### Content Guidelines

**Dialogue density:**
*   Major conversations: ~200–400 words
*   Minor interactions: ~50–100 words
*   Break long scenes into multiple nodes rather than one wall of text.

**Choice presentation:**
*   2–4 choices per meaningful node
*   At least one choice ungated
*   Gated choices should:
*   Communicate requirements in text
*   Reflect the player’s history (flags, convictions) when possible

**NPC voice:**
*   Give each major NPC:
*   A distinct speech pattern (formality, idioms, pacing)
*   Consistent personality across quests and acts
*   Let NPC reactions reflect:
*   Player’s past actions (memory flags)
*   Player’s perceived reputation/faction alignment
