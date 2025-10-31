# Development Guide

## Project Architecture

This game is built with a modular architecture to make it easy to expand and modify.

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
├── icon.svg                   # Project icon
├── README.md                  # User guide
├── GAMEPLAY.md                # Gameplay documentation
├── DEVELOPMENT.md             # This file
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
├── assets/                    # Game assets
│   ├── sprites/              # Character and object sprites
│   ├── tiles/                # Tileset images
│   ├── audio/                # Sound effects and music
│   └── fonts/                # Custom fonts
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

### Manual Testing Checklist
- [ ] Player movement in all directions
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

## Godot 4 Specific Notes

- This project uses Godot 4.2+ features
- Uses the new typed GDScript syntax
- Forward+ rendering method
- Signals use new `.emit()` syntax
- Scene instancing uses `@export` and `PackedScene`

## Getting Help

- Godot Documentation: https://docs.godotengine.org/
- GDScript Reference: https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/
- Godot Community: https://godotengine.org/community

## Testing

This project uses [GdUnit4](https://mikeschulze.github.io/gdUnit4/) for automated testing.

### Installing GdUnit4 for Local Development

GdUnit4 is **not** included in the repository. To run tests locally:

1. **Via Godot Asset Library** (recommended):
   - Open the project in Godot Editor (4.5 or later)
   - Go to AssetLib tab
   - Search for "GdUnit4"
   - Download and install the addon

2. **Manual Installation**:
   - Download [GdUnit4](https://github.com/MikeSchulze/gdUnit4/releases) v6.0.1 or later
   - Extract to `addons/gdUnit4/` in your project
   - The `addons/` directory is gitignored

### Running Tests

Tests run automatically in CI when you push changes or create a pull request.

**Local Testing** (requires GdUnit4 plugin installed):
- Open the project in Godot Editor
- Open the GdUnit4 inspector from the bottom panel
- Click "Run All Tests" or run individual test suites

**Test Structure**:
```
test/
├── CharacterStatsTest.gd          # Unit tests for CharacterStats
└── DialogueSystemIntegrationTest.gd  # Integration tests for DialogueSystem
```

### Writing Tests

**Unit Tests** - Test individual components in isolation:
```gdscript
class_name MyFeatureTest
extends GdUnitTestSuite

var _my_feature: MyFeature

func before_test():
    """Initialize before each test"""
    _my_feature = auto_free(MyFeature.new())

func test_my_functionality():
    """Test that my feature works correctly"""
    assert_int(_my_feature.calculate(2, 3)).is_equal(5)
```

**Integration Tests** - Test how components work together:
```gdscript
func test_character_dialogue_integration():
    """Test dialogue system with character stats"""
    var stats = auto_free(CharacterStats.new())
    var dialogue = auto_free(DialogueSystem.new())
    
    # Test interaction between systems
    dialogue.start_dialogue("start", stats)
    assert_bool(dialogue.select_option(0)).is_true()
```

### Best Practices

- Use `auto_free()` to automatically clean up test objects
- One assertion concept per test (but multiple assert calls are fine)
- Test both success and failure cases
- Name tests descriptively: `test_what_when_then`
- Use the `before()` and `before_test()` hooks for setup
- Follow the [GdUnit4 documentation](https://mikeschulze.github.io/gdUnit4/) for advanced features

## Contributing

When adding new features:
1. Follow the existing code style
2. Add comments for complex logic
3. Write tests for new functionality
4. Test thoroughly (both manual and automated)
5. Update documentation (this file, README, or GAMEPLAY)
6. Keep changes modular and reversible
