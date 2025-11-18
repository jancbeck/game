### Handover Notes: Gothic-Inspired Degradation RPG

**Date:** Tuesday, November 18, 2025
**Current Working Directory:** `/Users/jan/workspace/projects/game`

---

**1. Project Status: Core Architecture Established & Quest/Data Systems Initiated**

The foundational "Pattern 1: Immutable State Architecture" is now implemented and validated, and initial work on the Quest and Data loading systems has been completed.

*   **`scripts/core/game_state.gd`**: The `GameState` singleton is implemented. It holds the core game state, enforces immutability through `duplicate(true)` for state access, and uses a `dispatch(reducer)` method for all state transitions. It emits a `state_changed` signal.
*   **`scripts/core/player_system.gd`**: A basic `PlayerSystem` reducer is implemented. It contains a static `move` function that takes the current state and movement input, returning a new, updated state.
*   **`scripts/core/quest_system.gd`**: The core `QuestSystem` reducer is implemented. It handles quest completion, stat degradation, conviction accumulation, memory flag updates, and unlocking follow-up quests/locations as defined in the data. It includes validation for existing quests and approaches.
*   **`scripts/data/data_loader.gd`**: A static `DataLoader` class is implemented. It currently provides structured dummy data for the "rescue_prisoner" quest and a placeholder for "report_to_rebel_leader", enabling testing of the `QuestSystem` without external content files.
*   **`scripts/presentation/player_presentation.gd`**: A minimal presentation layer script is in place. It extends `CharacterBody3D`, subscribes to `GameState.state_changed`, and updates its `global_position` based on the player's position in the `GameState`.
*   **`scenes/test_room.tscn`**: A basic Godot scene with a `Camera3D` and a `CharacterBody3D` (using `player_presentation.gd` and a primitive capsule mesh) has been created.
*   **`project.godot`**:
    *   `GameState` is registered as an Autoload (singleton).
    *   Basic `move_left`, `move_right`, `move_forward`, `move_back` input actions are defined.
    *   The `run/main_scene` is currently set to `res://scenes/test_room.tscn` for direct testing of the core loop. This should be adjusted as the project's actual main scene develops.

---

**2. Validation & Testing**

*   **Unit Tests**: All unit tests are passing with `gdUnit4` across all implemented systems:
    *   `test/unit/test_game_state.gd`: 4 tests passing (initial state, dispatch, immutability, encapsulation).
    *   `test/unit/test_data_loader.gd`: 2 tests passing (dummy data for known and unknown quests).
    *   `test/unit/test_quest_system.gd`: 9 tests passing (violent/stealthy degradation, memory flags, non-existent/inactive quests, unlocking quests/locations, immutability).
*   **Code Quality**: All implemented GDScript files have been formatted with `gdformat` and successfully passed `gdlint --type-check`, adhering to the updated `AGENTS.md` standards.
*   **Visual Confirmation**: Running the project in Godot (with `scenes/test_room.tscn` as the main scene) allows for visual verification that pressing **W/A/S/D** moves the player capsule, confirming the input-to-state-to-UI pipeline is functional.

---

**3. Next Steps (Based on AGENTS.md - Phase 1 Deliverables)**

The immediate next focus should be on continuing with the "Phase 1: Foundation (Months 1-2)" deliverables, specifically:

*   **Refine "Pattern 2: Character Degradation Engine"**: Implement the full logic within `PlayerSystem` to manage character stats (flexibility, convictions) and integrate it with actions.
*   **Implement "Pattern 3: Thoughts → Words → Actions → Character Pipeline"**: Begin designing and implementing the framework for internal monologues and how player choices in these affect hidden conviction counters.
*   **Enhance Data Loader**: Transition `DataLoader` from returning dummy data to parsing actual content files (`.md` for quests, `.yarn` for dialogues, `.json` for characters/items/world data). This will involve implementing file reading and parsing logic.
*   **Continue Test-Driven Development**: For every new system or feature, create comprehensive unit tests (`gdUnit4`) and ensure all code adheres to `gdformat` and `gdlint --type-check` standards.

---

**4. Important Notes & Considerations**

*   **`main_scene`**: Remember that `project.godot`'s `run/main_scene` is currently set to `test_room.tscn`. This will likely need to be updated or managed as the game's actual main scene develops.
*   **`GDScript Toolkit 4.x`**: This toolkit is listed in `AGENTS.md` but has not been explicitly used or configured yet. Its integration might be a future task if specific functionalities are needed.
*   **`GameState` Instantiation in Tests**: In unit tests, `GameState` needs to be manually instantiated (`GameStateScript.new()`) and `_initialize_state()` called, as Autoloads are not automatically available in the test environment as they are in the running game.
*   **GdUnit4 Static Method Mocking**: There are known, persistent issues with `GdUnit4`'s `replace_class_method` and `restore_class_method` for mocking static functions. Some `test_quest_system.gd` tests that would utilize this functionality are currently commented out and will need to be revisited once a reliable mocking strategy is established or the issue is resolved within GdUnit4.

Good luck!