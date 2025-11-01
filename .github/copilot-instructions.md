# Copilot Instructions for Gothic Chronicles: The Aftermath

## Repository Overview
Post-Gothic 2 RPG with Disco Elysium mechanics. Godot 4.5.1 project with GDScript. Small prototype: 24 tests, ~670 lines of code. Features: character stats, 2d6 skill checks, dialogue trees, thought cabinet.

**Tech:** Godot 4.5.1 (Forward+), GDScript (typed), GdUnit4 v6.0.1, GDScript Toolkit 4.x, Git LFS for assets.

## Critical: Git LFS
Repository uses Git LFS (27 patterns in `.gitattributes` for images, audio, 3D models). **Always use `actions/checkout@v5` with `lfs: true`** when asset files are needed. Currently, only `icon.svg` is tracked (non-critical). The `gdscript-checks.yml` workflow already has `lfs: true`; `copilot-setup-steps.yml` does not.

## Build and Validation

### Prerequisites (copilot-setup-steps.yml handles these)
```bash
pip3 install "gdtoolkit>=4.0,<5.0" pre-commit
# Godot 4.5.1: wget https://github.com/godotengine/godot/releases/download/4.5.1-stable/Godot_v4.5.1-stable_linux.x86_64.zip
# GdUnit4 v6.0.1: install to addons/ from https://github.com/MikeSchulze/gdUnit4/releases/tag/v6.0.1
export GODOT_BIN=/tmp/Godot_v4.5.1-stable_linux.x86_64
```

### Linting (MANDATORY before commit)
```bash
gdformat --check scripts/  # Must exit 0
gdlint scripts/            # Must exit 0
```

### Testing
**DO NOT** run tests via command line (`addons/gdUnit4/runtest.sh` fails due to plugin init issues). Tests run automatically in CI via `MikeSchulze/gdUnit4-action@v1.2.2`. Expected: 24 tests (10 unit, 14 integration), ~30 seconds.

### Validation
```bash
$GODOT_BIN --path . -e --headless --quit-after 2000  # Imports project, exit 0 = success
```
Expect one harmless `icon.svg` error (LFS file).

## GitHub Workflows

**gdscript-checks.yml** (CI): Triggers on push/PR to `main`. Jobs: (1) static-checks (gdformat, gdlint), (2) unit-tests (GdUnit4 via `MikeSchulze/gdUnit4-action@v1.2.2`, 5min timeout). Uses `lfs: true` ✓.

**copilot-setup-steps.yml** (Agent Setup): Installs Python, gdtoolkit, pre-commit, Godot 4.5.1, GdUnit4 v6.0.1. Does NOT use `lfs: true` (currently not needed).

## Project Structure

**Key Directories:**
- `scripts/`: 6 GDScript files (character_stats.gd, dialogue_system.gd, thought_cabinet.gd, player.gd, npc.gd, game_ui.gd)
- `scenes/`: 4 .tscn files (main.tscn, player.tscn, npc.tscn, game_ui.tscn)
- `test/`: CharacterStatsTest.gd (10 tests), DialogueSystemIntegrationTest.gd (14 tests)
- `.github/workflows/`: copilot-setup-steps.yml, gdscript-checks.yml

**Core Systems:**
- **CharacterStats**: 4 attributes (Intellect/Psyche/Physique/Motorics), 8 skills, 2d6 checks, health/morale
- **DialogueSystem**: Node-based trees, skill checks (auto `nodeid_success`/`nodeid_fail` branches)
- **ThoughtCabinet**: Stat modifiers, 3 slots, 4 thoughts
- **Player/NPC/UI**: Signal-based communication, no tight coupling

**Config:** project.godot (Godot 4.5, GdUnit4 enabled), .gitattributes (27 LFS patterns), .pre-commit-config.yaml (gdtoolkit 4.5.0)

## Critical Rules

1. **Linting is mandatory**: `gdformat --check scripts/` and `gdlint scripts/` must pass before commit.
2. **No manual tests**: Tests run in CI only (command-line test runner broken).
3. **Typed GDScript**: Use type annotations (`var name: String`, `func foo() -> int`).
4. **Signal-based**: Use Godot signals for component communication. No tight coupling.
5. **Godot 4.5 syntax**: `.emit()` for signals, typed syntax, Forward+ renderer.
6. **Tests**: Use `auto_free()` in GdUnit4 tests. Unit tests in CharacterStatsTest.gd, integration in DialogueSystemIntegrationTest.gd.
7. **LFS assets**: New assets must match `.gitattributes` patterns. Update workflows if needed.
8. **Documentation**: DEVELOPMENT.md (APIs), README.md (user guide), GAMEPLAY.md (mechanics).

## Common Tasks

**Add skill:** Edit character_stats.gd (add var, update `update_skills_from_attributes()`, `get_skill_value()`, `get_stats_summary()`), update tests.

**Add dialogue:** Create DialogueNode/DialogueOption instances. For skill checks, create `nodeid_success` and `nodeid_fail` branches.

**Run game:** `$GODOT_BIN --path . -e` (opens editor, press F5) or `$GODOT_BIN --path .` (direct run).

## Root Files
project.godot, icon.svg (LFS), .gitattributes, .gitignore, .pre-commit-config.yaml, README.md, DEVELOPMENT.md, QUICKSTART.md, GAMEPLAY.md, TESTING_NOTES.md, PROJECT_SUMMARY.md, LICENSE.md

**Trust these instructions.** Validated by running all commands and reviewing documentation. Only search codebase for implementation details not covered here or if errors occur.
