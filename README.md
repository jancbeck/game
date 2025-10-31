# Gothic Chronicles: The Aftermath

A post-Gothic 2 RPG with mechanics inspired by Disco Elysium, built with Godot 4.

## Overview

This game is set after the events of Gothic 2, in a world recovering from the defeat of the dragons and the threat of Beliar. You play as a hero navigating the aftermath, dealing with the psychological and physical scars of the conflict.

## Game Mechanics

### Core Systems (Disco Elysium Inspired)

1. **Attribute System**
   - **Intellect**: Intelligence, reasoning, problem-solving
   - **Psyche**: Emotional intelligence, empathy, mental fortitude
   - **Physique**: Physical strength, endurance, health
   - **Motorics**: Dexterity, perception, coordination

2. **Skill System**
   Skills are derived from primary attributes and affect gameplay:
   - **Logic** (Intellect): Deductive reasoning, spotting inconsistencies
   - **Rhetoric** (Intellect + Psyche): Persuasion and argumentation
   - **Empathy** (Psyche): Understanding others' emotions and motivations
   - **Authority** (Psyche + Physique): Commanding presence and intimidation
   - **Perception** (Motorics + Intellect): Noticing details in the environment
   - **Endurance** (Physique): Physical stamina and damage resistance
   - **Pain Threshold** (Physique): Ability to endure physical hardship
   - **Shivers** (Psyche + Motorics): Sixth sense, premonitions

3. **Skill Check System**
   - Skill checks use 2d6 + skill value vs. difficulty
   - Success/failure branches in dialogue
   - Visual feedback on skill check results

4. **Thought Cabinet**
   - Internalize thoughts that provide bonuses/penalties
   - Thoughts reflect the game's narrative themes
   - Examples: "The Weight of Victory", "Slayer of Dragons", "Touched by Darkness"

5. **Dialogue System**
   - Rich, branching dialogue with multiple outcomes
   - Skill checks integrated into conversation
   - NPC reactions based on your attributes and choices

### Gothic 2 Setting Elements

- Set in the aftermath of defeating the dragons
- References to Khorinis, the mines, orcs, and Beliar
- Themes of trauma, recovery, and moving forward
- NPCs dealing with post-war consequences

## Controls

- **WASD / Arrow Keys**: Move character
- **E / Space**: Interact with NPCs
- **C**: Open Character Sheet
- **T**: Open Thought Cabinet
- **Mouse**: Select dialogue options

## Running the Game

### Prerequisites

1. Install Godot 4.2 or later from [godotengine.org](https://godotengine.org/download)
2. Download Godot for macOS

### Running on Mac

1. Open Godot Engine
2. Click "Import" and navigate to this project folder
3. Select the `project.godot` file
4. Click "Import & Edit"
5. Press F5 or click the "Run Project" button (play icon) in the top right

Alternatively, from command line:
```bash
/Applications/Godot.app/Contents/MacOS/Godot --path /path/to/game
```

## Project Structure

```
game/
├── project.godot          # Main project configuration
├── icon.svg               # Project icon
├── scenes/                # Game scenes
│   ├── main.tscn         # Main game scene
│   ├── player.tscn       # Player character
│   ├── npc.tscn          # NPC template
│   └── game_ui.tscn      # UI overlay
├── scripts/               # GDScript files
│   ├── player.gd         # Player controller
│   ├── npc.gd            # NPC behavior
│   ├── character_stats.gd # Stats and skill system
│   ├── dialogue_system.gd # Dialogue management
│   ├── thought_cabinet.gd # Thought cabinet system
│   └── game_ui.gd        # UI controller
└── assets/               # Game assets (placeholder)
    └── placeholder/      # Placeholder art
```

## Current Features

✅ Player movement system
✅ Character attribute and skill system
✅ Skill check mechanics (2d6 system)
✅ Dialogue system with branching paths
✅ Thought Cabinet with multiple thoughts
✅ NPC interaction system
✅ Character sheet UI
✅ Thought cabinet UI
✅ Dialogue UI with skill check feedback
✅ Health and morale tracking

## Placeholder Assets

This demo uses colored rectangles as placeholders:
- **Blue rectangle**: Player character
- **Orange rectangles**: NPCs
- **Dark gray**: Background
- **Green-gray**: Ground/walkable area

## Future Development

Content and assets to be added:
- Character sprites and animations
- Environment art and tiles
- Sound effects and music
- Additional dialogue trees
- More NPCs and locations
- Quest system
- Inventory system
- Combat system (if desired)
- Save/load functionality
- More thoughts for the cabinet
- Additional skill checks and consequences

## Technical Notes

- Built with Godot 4.2
- Uses GDScript for all game logic
- 2D top-down perspective
- Modular system architecture for easy expansion
- Signal-based communication between systems

## Development & Testing

This project has comprehensive testing and validation infrastructure:

- **Linting**: GDScript linting with gdlint
- **Testing**: Unit, integration, and E2E tests using GUT framework
- **CI/CD**: Automated checks on pull requests via GitHub Actions
- **Build Validation**: Ensures project compiles correctly

### Quick Start for Developers

```bash
# Install development tools
make install-tools

# Run linter
make lint

# Format code
make format

# Run all tests
make test

# Run all checks (lint + build + test)
make check
```

For detailed information, see [TESTING.md](TESTING.md).

## Testing the Demo

1. Start the game - you'll see the player (blue) and NPCs (orange)
2. Walk up to an NPC (press E when prompted)
3. Experience the dialogue system with skill checks
4. Press C to view your character stats
5. Press T to see available thoughts
6. Try different dialogue options to see skill checks in action

## Credits

- Inspired by Gothic 2 (Piranha Bytes)
- Mechanics inspired by Disco Elysium (ZA/UM)
- Built with Godot Engine

## License

This is a demonstration project. Actual game development would require proper licensing and permissions for using Gothic IP elements.
