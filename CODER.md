# Implementation Reference for AI Agents

**Scope**: Isometric 3D action-RPG with character degradation mechanics

**Playable without assets**: Yes (primitive shapes throughout development)

**Tech:** Godot 4.5.1 (Forward+), GDScript (typed), GDScript Toolkit 4.x, Git LFS for assets.

## I. State Schema (Source of Truth)

### Complete State Structure

```gdscript
GameState.state: Dictionary = {
    "player": {
        "position": Vector3,
        "health": int,           # Current: 0-100
        "max_health": int,       # Fixed: 100

        "flexibility": {
            "charisma": int,     # Range: 0-10, starts 10
            "cunning": int,      # Range: 0-10, starts 10
            "empathy": int       # Range: 0-10, starts 10
        },

        "convictions": {
            "violence_thoughts": int,      # Range: 0+, starts 0 (no max)
            "deceptive_acts": int,         # Range: 0+, starts 0 (no max)
            "compassionate_acts": int      # Range: 0+, starts 0 (no max)
        },

        "inventory": Array[String],  # Item IDs
        "equipment": {
            "weapon": String,    # Item ID or ""
            "armor": String      # Item ID or ""
        }
    },

    "world": {
        "current_location": String,
        "act": int,  # 1, 2, or 3

        "npc_states": Dictionary[String, {
            "alive": bool,
            "relationship": int,  # -100 to 100
            "memory_flags": Array[String]
        }],

        "location_flags": Dictionary[String, bool]
    },

    "quests": Dictionary[String, {
        "status": String,  # "available", "active", "completed", "failed"
        "approach_taken": String,
        "objectives_completed": Array[String]
    }],

    "dialogue_vars": Dictionary[String, Variant],

    "combat": {
        "active": bool,
        "enemies": Array,
        "available_abilities": Array
    },

    "meta": {
        "playtime_seconds": int,
        "save_version": String,
        "current_scene": String,
        "active_dialog_timeline": String,  # Current active Dialogic timeline ID
        "active_thought": String  # Legacy field, use active_dialog_timeline instead
    },

    "dialogic": {
        "vars": Dictionary,  # Dialogic variables
        "engine_state": Dictionary  # Full Dialogic engine state for save/load
    }
}
```

## II. System Signatures (Function Contracts)

### GameState (Node Autoload)

```gdscript
# Location: scripts/core/game_state.gd
# Note: Extends Node, autoloaded in project.godot

signal state_changed(new_state: Dictionary)

var state: Dictionary  # Property getter - returns _state.duplicate(true)
var _state: Dictionary  # Internal state storage

func dispatch(reducer: Callable) -> void
    # Calls reducer with current _state
    # If returns new Dictionary, updates _state and emits signal
    # Checks for state change using hash() before emitting
    # MUST verify reducer didn't mutate state in-place

func reset() -> void
    # Resets state to initial values by calling _initialize_state()

func snapshot_for_save() -> Dictionary
    # Returns deep copy of state with Dialogic.get_full_state() included
    # Use this instead of accessing state directly when saving

func restore_from_save(saved_state: Dictionary) -> void
    # Restores state from save file
    # Calls Dialogic.load_full_state() to restore dialogue state
    # Emits state_changed signal
```

### PlayerSystem

```gdscript
# Location: scripts/core/player_system.gd
class_name PlayerSystem
extends RefCounted

static func move(
    state: Dictionary,
    direction: Vector3,
    delta: float = 1.0 # Added default
) -> Dictionary
    # Updates state["player"]["position"]
    # Clamps to bounds: x/z in [-10, 10]
    # MUST return new Dictionary
    # MUST NOT mutate input state

static func modify_flexibility(
    state: Dictionary,
    stat: String,  # "charisma", "cunning", or "empathy"
    amount: int
) -> Dictionary
    # Updates state["player"]["flexibility"][stat]
    # Clamps result to [0, 10]
    # MUST return new Dictionary

static func modify_conviction(
    state: Dictionary,
    conviction: String,  # "violence_thoughts", "deceptive_acts", "compassionate_acts"
    amount: int
) -> Dictionary
    # Updates state["player"]["convictions"][conviction]
    # Clamps result to minimum of 0 (no maximum - convictions can grow indefinitely)
    # MUST return new Dictionary
```

### QuestSystem

```gdscript
# Location: scripts/core/quest_system.gd
class_name QuestSystem
extends RefCounted

static func check_prerequisites( # Renamed from can_start_quest, now returns bool
    state: Dictionary,
    quest_id: String
) -> bool
    # Checks prerequisites via DataLoader
    # Returns true if all prerequisites met
    # MUST NOT modify state

static func start_quest(
    state: Dictionary,
    quest_id: String
) -> Dictionary
    # Sets quest status to "active"
    # MUST check can_start_quest first
    # MUST return new Dictionary

static func complete_quest(
    state: Dictionary,
    quest_id: String,
    approach: String
) -> Dictionary
    # Loads quest data via DataLoader.get_quest(quest_id)
    # Applies degradation from approach_data["degrades"]
    # Updates convictions from approach_data["rewards"]["convictions"]
    # Sets memory flags from approach_data["rewards"]["memory_flags"]
    # Marks quest status "completed"
    # Unlocks follow-up quests from outcomes
    # MUST use PlayerSystem.modify_flexibility for stat changes
    # MUST return new Dictionary
```

### DataLoader (Singleton Autoload)

```gdscript
# Location: scripts/data/data_loader.gd
class_name DataLoader
extends RefCounted

static var _test_data: Dictionary # Added to allow mocking for tests

static func set_test_data(id: String, data: Dictionary) -> void # For testing
static func clear_test_data() -> void # For testing

static func get_quest(quest_id: String) -> Dictionary
    # Returns quest data from data/quests/*.json or {} if not found
    # Parses JSON
```

### SaveSystem

```gdscript
# Location: scripts/core/save_system.gd
class_name SaveSystem
extends RefCounted

const SAVE_PATH = "user://save.dat" # Updated to .dat

static func save_state(state: Dictionary) -> void # Renamed from save_game, no slot
    # Serializes state to user://save.dat using var_to_str
    # No return value, prints success/error

static func load_state() -> Dictionary # Renamed from load_game, no slot
    # Deserializes from user://save.dat using str_to_var
    # Returns state Dictionary or {} if file not found
```

## III. Architectural Rules (MUST/MUST NOT)

### State Management Rules

**MUST**:

- ✓ All game state in `GameState.state` Dictionary
- ✓ All state changes via `GameState.dispatch(reducer)`
- ✓ Reducers return new Dictionary (use `.duplicate(true)`)
- ✓ Check `is_same_instance()` to verify no mutation (covered by `duplicate(true)`)

**MUST NOT**:

- ✗ Store state in system member variables
- ✗ Mutate state Dictionary in-place
- ✗ Access state directly (always via GameState.state)
- ✗ Modify state from presentation layer

### System Design Rules

**MUST**:

- ✓ Extend `RefCounted`, not `Node`
- ✓ Use `static func` only (no instance methods)
- ✓ Type all parameters and returns
- ✓ Include docstring with example

**MUST NOT**:

- ✗ Reference Godot nodes in core systems
- ✗ Use ` @onready` or scene tree access
- ✗ Store instance state
- ✗ Use signals in core systems (only in presentation)

### Data Flow Rules

**MUST**:

- ✓ Load content from data/ files via DataLoader
- ✓ Parse YAML frontmatter in quest .md files
- ✓ Use PlayerSystem for stat modifications
- ✓ Validate prerequisites before state changes

**MUST NOT**:

- ✗ Hardcode quest/dialogue text in code
- ✗ Directly manipulate flexibility/conviction values
- ✗ Skip validation checks
- ✗ Assume data files exist without checking

### Presentation Layer Rules

**MUST**:

- ✓ Connect to `GameState.state_changed` signal
- ✓ Read state, never modify
- ✓ Dispatch actions via `GameState.dispatch()`
- ✓ Update visuals in `_on_state_changed()`

**MUST NOT**:

- ✗ Contain game logic
- ✗ Access other systems directly
- ✗ Modify GameState.state directly
- ✗ Store game state in node variables

## IV. Code Patterns (Copy These)

### Pattern: Pure Reducer Function

```gdscript
# Template for all system functions
static func system_action(
    state: Dictionary,
    param1: Type,
    param2: Type
) -> Dictionary:
    # 1. Validate inputs
    if not _validate_inputs(state, param1): # Example of _validate_inputs - replace with actual logic
        push_error("Invalid input")
        return state  # Return unchanged on error

    # 2. Create deep copy
    var new_state := state.duplicate(true)

    # 3. Load data if needed
    var data = DataLoader.get_something(param1) # Example, replace with actual DataLoader call
    if data.is_empty():
        push_error("Data not found")
        return state

    # 4. Apply changes to new_state
    new_state["some"]["path"] = "new_value" # Example, replace with actual changes

    # 5. Clamp values to valid ranges
    new_state["player"]["flexibility"]["charisma"] = clampi(
        new_state["player"]["flexibility"]["charisma"],
        0, 10
    )

    # 6. Return new state
    return new_state
```

### Pattern: Presentation Layer

```gdscript
# Template for all presentation scripts
extends Node  # or CharacterBody3D, etc.

@onready var some_node: Node = $SomeNode # Example @onready

func _ready() -> void:
    GameState.state_changed.connect(_on_state_changed)
    call_deferred("_on_state_changed", GameState.state)  # Initial sync after node is ready

func _on_state_changed(new_state: Dictionary) -> void:
    # Update visuals from state
    # NO LOGIC HERE - just display current state
    if some_node: # Check if node is valid
        some_node.property = new_state["player"]["some_value"] # Example

func _input(event: InputEvent) -> void:
    # Handle input
    if event.is_action_pressed("some_action"):
        # Dispatch action to state
        GameState.dispatch(
            func(s: Dictionary) -> Dictionary:
                return SomeSystem.some_action(s, "params") # Example with static call
        )
```

### Pattern: Quest Trigger

**Location**: scripts/core/quest_trigger.gd

**Purpose**: Area3D node that triggers quest interactions and Dialogic timelines

```gdscript
# Template: scripts/core/quest_trigger.gd
extends Area3D

@export var quest_id: String = ""
@export var interaction_prompt: String = "Press 'E' to interact"
@export var timeline_id: String = ""  ## Dialogic timeline to start on interaction

var player_in_range: bool = false
var game_state = GameState


func _ready():
    if quest_id.is_empty():
        push_warning("QuestTrigger: quest_id not set for %s" % name)

    # Check initial state and remove if quest is already active/completed
    _check_and_remove_if_completed()

    # Listen for state changes to remove trigger when quest is completed
    if game_state.state_changed.connect(_on_state_changed) != OK:
        push_warning("QuestTrigger: Failed to connect to state_changed signal")


func _on_state_changed(_new_state: Dictionary) -> void:
    _check_and_remove_if_completed()


func _check_and_remove_if_completed() -> void:
    # Remove trigger if quest is already active or completed
    if game_state.state.has("quests") and game_state.state["quests"].has(quest_id):
        var status = game_state.state["quests"][quest_id]["status"]
        if status != "available":
            queue_free()


func _on_body_entered(body: Node3D):
    if body.name == "Player":
        player_in_range = true
        var can_start = QuestSystem.check_prerequisites(game_state.state, quest_id)
        if can_start:
            print("QuestTrigger: Player entered range (Ready)")
            # TODO: Show interaction_prompt in UI
        else:
            print("QuestTrigger: Player entered range (Locked)")


func _on_body_exited(body: Node3D):
    if body.name == "Player":
        print("QuestTrigger: Player exited range")
        player_in_range = false
        # TODO: Hide interaction_prompt in UI


func _input(event: InputEvent):
    if player_in_range and event.is_action_pressed("interact"):
        print("QuestTrigger: Interact pressed")
        if not quest_id.is_empty():
            # Preferred: Start Dialogic timeline if configured
            # The timeline handles quest start/completion via signals
            if not timeline_id.is_empty():
                print("QuestTrigger: Starting Dialogic timeline '%s'" % timeline_id)
                var dialog_system = get_node_or_null("/root/DialogSystem")
                if dialog_system and dialog_system.has_method("start_timeline"):
                    dialog_system.start_timeline(timeline_id)
                else:
                    push_error("DialogSystem not found. Add it as autoload.")
                return

            # Fallback: Direct quest start (deprecated, use timeline_id instead)
            if not QuestSystem.check_prerequisites(game_state.state, quest_id):
                print("QuestTrigger: Locked - Prerequisites not met")
                return

            game_state.dispatch(func(state): return QuestSystem.start_quest(state, quest_id))
            print("Quest started via legacy fallback.")
```

**Usage**:
1. **Preferred**: Set both `quest_id` and `timeline_id`. The timeline handles all quest logic via signals.
2. **Legacy**: Set only `quest_id` for direct quest start (no dialogue, deprecated).

**Timeline signals** (see Pattern: Thoughts):
- `start_quest:quest_id`
- `complete_quest:quest_id:approach`
- `modify_conviction:name:amount`
- `modify_flexibility:name:amount`
```

### Pattern: DialogSystem (Dialogic 2 Integration)

**Location**: scripts/ui/dialog_system.gd (autoload)

**Purpose**: Bridge between Dialogic timelines and GameState

**Timeline Signal Format**:
- `start_quest:quest_id` - Starts quest via GameStateActions
- `complete_quest:quest_id:approach` - Completes with approach
- `modify_conviction:name:delta` - Changes conviction
- `modify_flexibility:name:delta` - Changes flexibility stat

**Timeline Creation**:
- Use Dialogic 2 editor (Plugins → Dialogic)
- Save to: `data/timelines/[timeline_id].dtl`
- Use signal events to trigger game state changes
- NEVER modify GameState directly from timelines

**Example Timeline Structure** (actual Dialogic 2 .dtl syntax):
```
You found the camp. Now you must convince them you are useful.
- Offer your services
	[signal arg="start_quest:join_rebels"]
	[wait time="0.5"]
	[signal arg="complete_quest:join_rebels:diplomatic"]
- I need more time to think.
	You can't delay this decision forever.
```

**Conviction Gating in Timelines** (actual Dialogic 2 .dtl syntax):
```
You stand before the sealed door. The air hums with dark energy.
- [Analyze] Decipher the warnings. | [if GameStateActions.get_flexibility("cunning") >= 3]
	You trace the ancient glyphs. Cold logic takes hold.
	do GameStateActions.complete_quest("investigate_ruins", "analyze")
- [Force] Smash the door. | [if GameStateActions.get_conviction("violence_thoughts") >= 5]
	You channel your rage into a single blow. The stone cracks.
	do GameStateActions.complete_quest("investigate_ruins", "force")
- Leave.
	You cannot turn back now. The story demands an ending.
	jump quest_investigate_ruins_resolution
```

**Key Dialogic 2 Syntax**:
- **Emit signals**: `[signal arg="command:param1:param2"]`
- **Execute code**: `do GameStateActions.method_name(params)`
- **Conditional choices**: `- Choice text | [if condition]`
- **Wait**: `[wait time="seconds"]`
- **Jump to timeline**: `jump timeline_id`
- **Comments**: Lines without special markers are dialogue text

**MUST**:
- All state changes via signal events
- Timeline IDs match quest IDs
- Use GameStateActions API only
- Test timeline in Dialogic editor before integrating

**MUST NOT**:
- Directly call GameState.dispatch from timelines
- Store game logic in timeline variables
- Bypass GameStateActions API

### Pattern: Thoughts (Dialogic Timelines)

**Implementation**: Thoughts are implemented as Dialogic timelines, not as a separate system.

**Naming Convention**:
- Thought timelines: `thought_[context]` (e.g., `thought_before_join_rebels`)
- Quest intro timelines: `quest_[quest_id]_intro`
- Quest resolution timelines: `quest_[quest_id]_resolution`

**Thought Timeline Structure**:
Thoughts present internal monologue choices that affect convictions and flexibility.

**Example** (from `join_rebels.dtl`):
```
Words are stronger than steel. Or are they just quieter?
- Violence is a failure of imagination.
	[signal arg="modify_conviction:compassionate_acts:2"]
	[signal arg="modify_conviction:violence_thoughts:-1"]
- It worked this time. Next time might require a blade.
	[signal arg="modify_conviction:violence_thoughts:1"]
- I manipulated them perfectly.
	[signal arg="modify_conviction:deceptive_acts:2"]
```

**Triggering Thoughts**:
- Thoughts are triggered by starting the appropriate Dialogic timeline via `DialogSystem.start_timeline(timeline_id)`
- The `active_thought` field in `state["meta"]` tracks if a thought timeline is active (managed by DialogSystem)
- QuestTriggers can specify a `timeline_id` to start before quest logic

**Pattern**:
1. Player encounters QuestTrigger
2. QuestTrigger starts thought timeline (if configured)
3. Player makes choices that modify convictions/flexibility
4. Timeline completes and triggers quest start/completion
5. Quest logic applies approach-based degradation

**MUST**:
- Use `[signal arg="..."]` format for state changes
- Choices should represent distinct philosophical positions
- Each option affects convictions or flexibility (2-5 point changes)

**MUST NOT**:
- Create a separate ThoughtSystem (use Dialogic timelines)
- Hardcode thought content in GDScript
- Store thought data in JSON (use .dtl files)

## V. Test Requirements

### Every System Function MUST Have Tests

**Test structure**:

```gdscript
# test/unit/test_[system_name].gd
extends GdUnitTestSuite # Updated to GdUnitTestSuite

var initial_state: Dictionary

func before_each() -> void:
    # Create clean state for each test
    initial_state = {
        "player": {
            "flexibility": {"charisma": 10, "cunning": 10, "empathy": 10},
            "convictions": {"violence_thoughts": 0, "deceptive_acts": 0, "compassionate_acts": 0}
        },
        "quests": {},
        "meta": {} # Added meta for thought system tests
    }

func test_function_name_describes_behavior() -> void:
    # Arrange
    initial_state["some_setup"] = "value" # Example

    # Act
    var result = System.function(initial_state, "params") # Example

    # Assert
    assert_that(result["expected"]["path"]).is_equal("expected_value") # Example

func test_immutability() -> void:
    var copy_before = initial_state.duplicate(true)

    var result = System.function(initial_state, "params") # Example

    assert_that(initial_state).is_equal(copy_before)
    assert_that(result).is_not_same(initial_state)
```

### Required Test Cases Per System

**For every reducer function, test**:

1. ✓ Happy path (valid inputs → expected output)
2. ✓ Immutability (original state unchanged)
3. ✓ Boundary values (min/max ranges)
4. ✓ Invalid inputs (returns unchanged state)
5. ✓ Data not found (graceful failure)

**Example**:

```gdscript
# Required tests for PlayerSystem.modify_flexibility

func test_modify_flexibility_updates_stat():
    # Happy path

func test_modify_flexibility_immutability():
    # Original state unchanged

func test_modify_flexibility_clamps_to_maximum():
    # Can't exceed 10

func test_modify_flexibility_clamps_to_minimum():
    # Can't go below 0

func test_modify_flexibility_invalid_stat_name():
    # Returns unchanged state
```

## VII. Common Patterns

### Loading Data from Files

```gdscript
# Always check if data exists
var quest_data = DataLoader.get_quest("quest_id") # Example
if quest_data.is_empty():
    push_error("Quest not found: " + "quest_id")
    return state  # Return unchanged

# Access nested data safely
var approach_data = quest_data.get("approaches", {}).get("approach", {}) # Example
if approach_data.is_empty():
    push_error("Approach not found: " + "approach")
    return state
```

### Modifying Multiple Stats

```gdscript
# Use PlayerSystem functions, don't modify directly
var new_state = state.duplicate(true)

for stat in approach_data.get("degrades", {}): # Example
    new_state = PlayerSystem.modify_flexibility(
        new_state,
        stat,
        approach_data["degrades"][stat]
    )

for conviction in approach_data.get("rewards", {}).get("convictions", {}): # Example
    new_state = PlayerSystem.modify_conviction(
        new_state,
        conviction,
        approach_data["rewards"]["convictions"][conviction]
    )

return new_state
```

### Setting Memory Flags

```gdscript
# Format: npc_id_flag_name
# Parse using rsplit to allow underscores in npc_id

for flag in memory_flags: # Example
    var parts = flag.rsplit("_", true, 1)
    if parts.size() != 2:
        push_warning("Invalid memory flag format: " + "flag")
        continue

    var npc_id = parts[0]
    var flag_name = parts[1]

    if not new_state["world"]["npc_states"].has(npc_id):
        push_warning("NPC not found: " + npc_id)
        continue

    if not new_state["world"]["npc_states"][npc_id]["memory_flags"].has(flag_name):
        new_state["world"]["npc_states"][npc_id]["memory_flags"].append(flag_name)
```

## VIII. Code Quality Checklist

Before submitting code, verify:

**Formatting**:

- [ ] Run `source .venv/bin/activate && gdformat scripts/ &- gdlint scripts/`
- [ ] No linter warnings
- [ ] Import - generate UIDs: `/Applications/Godot.app/Contents/MacOS/Godot --path . -e --headless --quit-after 2000`

**Type Safety**:

- [ ] All parameters have type hints
- [ ] All returns have type hints
- [ ] Dictionaries use typed syntax where possible

**Documentation**:

- [ ] Docstring with example usage
- [ ] Comments explain "why", not "what"
- [ ] No commented-out code

**Testing**:

- [ ] Unit tests for function added. Use mcp context7.com/websites/mikeschulze_github_io-gdunit4 to lookup how to use gdunit4. Do NOT use GUT.
- [ ] All tests pass locally `/Applications/Godot.app/Contents/MacOS/Godot --headless -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a res://test`
- [ ] Test names describe behavior

**Architecture Compliance**:

- [ ] Follows immutable state pattern
- [ ] No hardcoded content
- [ ] Uses DataLoader for data
- [ ] Presentation layer has no logic

## IX. Quick Reference

### Common State Paths

```gdscript
# Player stats
state["player"]["flexibility"]["charisma"]  # 0-10
state["player"]["convictions"]["violence_thoughts"]  # 0-100

# Quest status
state["quests"][quest_id]["status"]  # "available", "active", "completed"

# NPC memory
state["world"]["npc_states"][npc_id]["memory_flags"]  # Array[String]

# Combat
state["combat"]["active"]  # bool
state["combat"]["enemies"]  # Array
state["combat"]["available_abilities"]  # Array

# Dialogic
state["meta"]["active_dialog_timeline"]  # Current timeline ID or ""
state["dialogic"]["vars"]  # Dialogic variables
state["dialogic"]["engine_state"]  # Full Dialogic state (for save/load)
```

### Common System Calls

```gdscript
# Move player
PlayerSystem.move(state, direction, delta)

# Modify stats (from systems)
PlayerSystem.modify_flexibility(state, "charisma", -2)
PlayerSystem.modify_conviction(state, "violence_thoughts", 3)

# Get stats (for conditions in Dialogic)
GameStateActions.get_flexibility("charisma")  # Returns int
GameStateActions.get_conviction("violence_thoughts")  # Returns int

# Quest operations
QuestSystem.check_prerequisites(state, quest_id)  # bool
QuestSystem.start_quest(state, quest_id)
QuestSystem.complete_quest(state, quest_id, "approach") # Example

# GameStateActions (for Dialogic timelines)
GameStateActions.start_quest(quest_id)
GameStateActions.complete_quest(quest_id, approach)
GameStateActions.modify_conviction(conviction_name, amount)
GameStateActions.modify_flexibility(stat_name, amount)
GameStateActions.can_start_quest(quest_id)  # Returns bool

# Save/Load
SaveSystem.save_state(state)
SaveSystem.load_state()  # Returns Dictionary
```

---

**End of AGENTS.md**

This document contains everything needed to generate code.

If you need rationale or philosophy, see ARCHITECTURE.md.

If you need timeline or milestones, see PROJECT.md.

If you need content formats, see CONTENT_SPEC.md.
