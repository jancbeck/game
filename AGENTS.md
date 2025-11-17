# Copilot Instructions for JägerJäger

## Repository Overview

Mortal Combat-inspired 3D fighting game prototype. Godot 4.5.1 project with GDScript.

**Tech:** Godot 4.5.1 (Forward+), GDScript (typed), GDScript Toolkit 4.x, Git LFS for assets.

## Build - Validation

```bash
# Format - lint
source .venv/bin/activate
gdformat scripts/ &- gdlint scripts/

# Import - generate UIDs
/Applications/Godot.app/Contents/MacOS/Godot --path . -e --headless --quit-after 2000

# Run tests using gdUnit4 (smoke tests for fast iteration)
/Applications/Godot.app/Contents/MacOS/Godot --headless -s res://addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a res://test
```

## Animations

Brute library:

- Attack 360 low

- Attack combo 2

- Equip over shoulder

- Jump short

- React from right

- Tpose

- Unarmed Jump short

- attack 360 high

- attack backhand

- attack combo

- attack downward

- attack horizontal

- block idle

- crouch idle

- crouch to stand

- equip underarm

- idle looking1

- idle looking2

- idle standing

- jump

- kick1

- kick2

- react from left

- react gut

- react-block

- run back

- run forward

- taunt battlecry

- taunt chest thump

- turn left

- turn right

- unarmed idle

- unarmed idle looking 1

- unarmed idle looking2

- unarmed jump

- unarmed jump running

- unarmed run back

- unarmed run forward

- unarmed turn left

- unarmed turn right

- unarmed walk back

- unarmed walk forward

- unequip over shoulder

- unequip underarm

- walk back

- walk forward

- walk left

- walk-right

## Critical Rules

- **Typed GDScript mandatory**: Explicit types for all vars to avoid inference errors
- **Linting must pass**: `gdformat` and `gdlint` before commits
- **Godot 4.5 syntax**: `.emit()` for signals, typed annotations
- **Signal-based communication**: Avoid tight coupling
- **Generate UIDs**: Always run headless import after creating scenes/scripts
- **Comments**: Explain "why" and complex logic, not self-explanatory "what"
- **Tests**: Keep smoke tests short and focused on core values/behavior
- **Keep AGENTS.md updated** with system changes
