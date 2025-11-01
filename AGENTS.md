# Copilot Instructions for Gothic Chronicles: The Aftermath

## Repository Overview

Post-Gothic 2 RPG with Disco Elysium mechanics. Godot 4.5.1 project with GDScript.

**Tech:** Godot 4.5.1 (Forward+), GDScript (typed), GdUnit4 v6.0.1, GDScript Toolkit 4.x, Git LFS for assets.

### Core Systems

#### 1. Character Stats System (`scripts/character_stats.gd`)

**Purpose**: Manages character attributes, skills, and performs skill checks.

**Key Features**:

- 4 primary attributes (Intellect, Psyche, Physique, Motorics)
- 8 derived skills
- 2d6 skill check system
- Signal-based communication for stat changes

**API**:

```gdscript
# Perform a skill check
var result = stats.perform_skill_check("rhetoric", 8)
# Returns: { skill, skill_value, roll, total, difficulty, success, margin }

# Modify attributes
stats.modify_attribute("intellect", 1)  # +1 to intellect

# Get skill values
var logic_value = stats.get_skill_value("logic")
```

#### 2. Thought Cabinet System (`scripts/thought_cabinet.gd`)

**Purpose**: Manages thoughts that can be internalized for stat bonuses/penalties.

**Key Features**:

- Dynamic thought system with effects
- Limited active thought slots (3 by default)
- Easy to add new thoughts

**API**:

```gdscript
# Create a new thought
var thought = ThoughtCabinet.Thought.new(
    "thought_id",
    "Thought Title",
    "Description of the thought",
    5.0,  # Time to internalize (seconds)
    {"skill_name": modifier}  # Effects
)

# Add and internalize
thought_cabinet.add_available_thought(thought)
thought_cabinet.internalize_thought("thought_id")

# Get total effects from all thoughts
var effects = thought_cabinet.get_total_effects()
```

#### 3. Dialogue System (`scripts/dialogue_system.gd`)

**Purpose**: Handles branching dialogue with integrated skill checks.

**Key Features**:

- Node-based dialogue tree
- Skill check integration
- Success/fail branches
- Signal emissions for UI updates

**API**:

```gdscript
# Create dialogue nodes
var node = DialogueSystem.DialogueNode.new("node_id", "Speaker", "Text")

# Add options
var option = DialogueSystem.DialogueOption.new(
    "Option text",
    "next_node_id",
    "skill_name",  # Optional: for skill checks
    difficulty     # Optional: skill check difficulty
)
node.add_option(option)

# Start and progress dialogue
dialogue_system.start_dialogue("start", character_stats)
dialogue_system.select_option(0)  # Select first option
```

#### 4. Player Controller (`scripts/player.gd`)

**Purpose**: Handles player movement, input, and interaction.

**Key Features**:

- WASD/Arrow key movement
- Interaction system
- References to stats and thought cabinet

**Extension Points**:

- Add sprint mechanic
- Add inventory system
- Add combat system

#### 5. NPC System (`scripts/npc.gd`)

**Purpose**: Manages NPC behavior and interactions.

**Key Features**:

- Area-based interaction detection
- Dialogue integration
- Configurable per-NPC

**Extension Points**:

- Add AI behavior
- Add patrol routes
- Add day/night routines

#### 6. UI System (`scripts/game_ui.gd`)

**Purpose**: Manages all UI elements and player feedback.

**Key Features**:

- Dialogue display
- Character sheet
- Thought cabinet display
- Skill check notifications
- Status bars

**Extension Points**:

- Add quest log
- Add inventory UI
- Add map

## Adding New Content

### Adding a New Skill

1. In `character_stats.gd`, add the skill variable:

```gdscript
var new_skill: int = 2
```

2. Update the `update_skills_from_attributes()` function:

```gdscript
new_skill = attribute1 + attribute2
```

3. Add the skill to `get_skill_value()`:

```gdscript
"new_skill": return new_skill
```

4. Update `get_stats_summary()` to display it.

### Adding a New Thought

In `thought_cabinet.gd`'s `_ready()` function:

```gdscript
add_available_thought(Thought.new(
    "unique_id",
    "Thought Title",
    "Detailed description of the thought and its implications.",
    10.0,  # Time to internalize
    {
        "skill_name": modifier_value,
        "health": -10,
        "morale": 5
    }
))
```

### Creating New Dialogue

1. In your NPC or dialogue manager script:

```gdscript
var dialogue = {}

# Create start node
var start = DialogueNode.new("start", "NPC Name", "Opening dialogue")
start.add_option(DialogueOption.new("Response 1", "node2"))
start.add_option(DialogueOption.new("[Skill] Special option", "node3", "skill_name", 7))
dialogue["start"] = start

# Create follow-up nodes
var node2 = DialogueNode.new("node2", "NPC Name", "Response to option 1")
node2.add_option(DialogueOption.new("Continue", "end"))
dialogue["node2"] = node2

# Create skill check success/fail branches
var node3_success = DialogueNode.new("node3_success", "NPC Name", "Success response")
var node3_fail = DialogueNode.new("node3_fail", "NPC Name", "Failure response")
dialogue["node3_success"] = node3_success
dialogue["node3_fail"] = node3_fail

# Create end node
var end = DialogueNode.new("end", "NPC Name", "Goodbye")
dialogue["end"] = end
```

2. The system automatically looks for `[nodeid]_success` and `[nodeid]_fail` branches for skill checks.

### Adding a New NPC

1. Duplicate `scenes/npc.tscn`
2. Modify the `npc_name` export variable
3. Create custom dialogue in the NPC's script or link to a shared dialogue system
4. Place in the scene

### Adding a New Scene/Location

1. Create a new scene in `scenes/`
2. Add environment elements (use ColorRect for now, replace with sprites later)
3. Add Player instance
4. Add NPCs
5. Add UI instance
6. Update navigation/transitions as needed

## File Organization

```
game/
├── project.godot              # Godot project config
├── scenes/                    # All scene files (.tscn)
│   ├── main.tscn             # Main game scene
│   ├── player.tscn           # Player prefab
│   ├── npc.tscn              # NPC prefab
│   └── game_ui.tscn          # UI overlay
├── scripts/                   # All GDScript files (.gd)
│   ├── player.gd
│   ├── npc.gd
│   ├── character_stats.gd
│   ├── dialogue_system.gd
│   ├── thought_cabinet.gd
│   └── game_ui.gd
└── .godot/                   # Godot generated files (ignored)
```

## Best Practices

### Script Organization

- One class per file
- Use `class_name` for globally accessible classes
- Document public APIs with comments
- Use signals for loose coupling

### Scene Organization

- Keep scenes modular and reusable
- Use instancing for repeated elements
- Export variables for easy configuration
- Use groups for batch operations

### Signal-Based Communication

Instead of direct references:

```gdscript
# Good: Signal-based
signal player_action()
player_action.emit()

# Avoid: Direct coupling
get_node("../UI/Panel").update()
```

### Performance Tips

- Use `@onready` for node references that won't change
- Cache frequently accessed nodes
- Use object pooling for projectiles/effects
- Profile before optimizing

## Testing

### Common scenarios to test

- [ ] NPC interaction triggers correctly
- [ ] Dialogue displays properly
- [ ] Skill checks calculate correctly
- [ ] Character sheet shows accurate data
- [ ] Thought cabinet displays thoughts
- [ ] UI responds to keyboard input
- [ ] Status bars update in real-time

### Edge Cases to Test

- Multiple rapid interactions
- Opening UI panels while in dialogue
- Skill checks at minimum/maximum values
- Full thought cabinet (3/3 slots)

## Expansion Ideas

### Short-term

- [ ] Add more dialogue trees
- [ ] Create additional NPCs with unique personalities
- [ ] Add more thoughts related to Gothic lore
- [ ] Implement basic inventory system
- [ ] Add simple quest tracking

### Medium-term

- [ ] Replace placeholder graphics with sprites
- [ ] Add ambient sound and music
- [ ] Implement save/load system
- [ ] Create multiple locations/scenes
- [ ] Add character customization

### Long-term

- [ ] Full narrative campaign
- [ ] Combat system (if desired)
- [ ] Advanced AI for NPCs
- [ ] Dynamic world events
- [ ] Multiple endings based on choices

## Gothic 2 Lore Integration

When adding content, consider these Gothic 2 elements:

- **Locations**: Khorinis, Valley of Mines, Monastery, City
- **Factions**: Militia, Fire Mages, Water Mages, Mercenaries, Farmers
- **Key NPCs**: Xardas, Milten, Diego, Lester, Gorn
- **Lore**: Three Gods (Innos, Beliar, Adanos), Magic, Ore
- **Post-game themes**: Rebuilding, trauma, peace after war

## Disco Elysium Mechanics Integration

When designing new systems, keep these DE principles:

- Skills as characters (they "speak" through internal dialogue)
- Failure is interesting (failed checks open new paths)
- Everything has a cost (thoughts give bonuses BUT also penalties)
- Psychology matters (mental stats as important as physical)
- World building through dialogue (not just exposition)

## Build and Validation

### Testing

```bash
export GODOT_BIN=/tmp/Godot_v4.5.1-stable_linux.x86_64
$GODOT_BIN --path . -e --headless --quit-after 2000  # Imports project, exit 0 = success

# Run tests using gdUnit4 command-line tool (works without plugin enabled in project settings)
# Use -a res://test to run all tests in the test directory
$GODOT_BIN --headless -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a res://test

# Alternative: Use the runtest.sh wrapper script
chmod +x ./addons/gdUnit4/runtest.sh
./addons/gdUnit4/runtest.sh -a res://test
```

### Type Checking

Type checking validates GDScript syntax and type annotations by loading the project in Godot editor headless mode:

```bash
# Run type check (parses all scripts, fails on syntax errors)
$GODOT_BIN --headless --quit --editor --path .
```

## Project Structure

## Critical Rules

1. **Linting is mandatory**: `gdformat --check scripts/` and `gdlint scripts/` must pass before commit.
2. **Run manual tests**
3. **Typed GDScript**: Use type annotations (`var name: String`, `func foo() -> int`).
4. **Signal-based**: Use Godot signals for component communication. No tight coupling.
5. **Godot 4.5 syntax**: `.emit()` for signals, typed syntax, Forward+ renderer.
6. **Tests**: Use `auto_free()` in GdUnit4 tests. Unit tests in CharacterStatsTest.gd, integration in DialogueSystemIntegrationTest.gd.
7. **LFS assets**: New assets must match `.gitattributes` patterns. Update workflows if needed.
8. **Documentation**: DEVELOPMENT.md (APIs), README.md (user guide), GAMEPLAY.md (mechanics).
