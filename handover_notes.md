### Handover Notes: Gothic-Inspired Degradation RPG

**Date:** Tuesday, November 18, 2025
**Current Working Directory:** `/Users/jan/workspace/projects/game`

---

**1. Project Status: Core Architecture Established**

The foundational "Pattern 1: Immutable State Architecture" is now implemented and validated.

*   **`scripts/core/game_state.gd`**: The `GameState` singleton is implemented. It holds the core game state, enforces immutability through `duplicate(true)` for state access, and uses a `dispatch(reducer)` method for all state transitions. It emits a `state_changed` signal.
*   **`scripts/core/player_system.gd`**: A basic `PlayerSystem` reducer is implemented. It contains a static `move` function that takes the current state and movement input, returning a new, updated state.
*   **`scripts/presentation/player_presentation.gd`**: A minimal presentation layer script is in place. It extends `CharacterBody3D`, subscribes to `GameState.state_changed`, and updates its `global_position` based on the player's position in the `GameState`.
*   **`scenes/test_room.tscn`**: A basic Godot scene with a `Camera3D` and a `CharacterBody3D` (using `player_presentation.gd` and a primitive capsule mesh) has been created.
*   **`project.godot`**:
    *   `GameState` is registered as an Autoload (singleton).
    *   Basic `move_left`, `move_right`, `move_forward`, `move_back` input actions are defined.
    *   The `run/main_scene` is currently set to `res://scenes/test_room.tscn` for direct testing of the core loop. This should be adjusted as the project's actual main scene develops.

---

**2. Validation & Testing**

*   **Unit Tests**: All 4 unit tests in `test/unit/test_game_state.gd` are passing with `gdUnit4`. These tests specifically verify:
    *   Initial state values.
    *   Correct state updates via `dispatch()`.
    *   **Reducer immutability** (reducers do not mutate input state).
    *   **State encapsulation** (`GameState.state` returns a copy, preventing external direct mutation).
*   **Code Quality**: All implemented GDScript files have been formatted with `gdformat` and successfully passed `gdlint --type-check`, adhering to the updated `AGENTS.md` standards.
*   **Visual Confirmation**: Running the project in Godot (with `scenes/test_room.tscn` as the main scene) allows for visual verification that pressing **W/A/S/D** moves the player capsule, confirming the input-to-state-to-UI pipeline is functional.

---

**3. Next Steps (Based on AGENTS.md - Phase 1 Deliverables)**

The immediate next focus should be on continuing with the "Phase 1: Foundation (Months 1-2)" deliverables, specifically:

*   **Implement "Pattern 2: Character Degradation Engine"**: Begin implementing the core mechanics related to stat inversion, thought accumulation, and option gating.
*   **Implement "Pattern 3: Thoughts → Words → Actions → Character Pipeline"**: Integrate the layered system where internal monologues, dialogue options, action availability, and character identity interact.
*   **Quest System Implementation**: Start working on the `QuestSystem` as outlined in `AGENTS.md`, which will heavily rely on the degradation engine and data architecture.
*   **Data Loader**: Implement a `DataLoader` system to parse the content file formats (`.md`, `.yarn`, `.json`) as described in "Pattern 5: Content-Code Separation". This is critical for the quest and dialogue systems.
*   **Continue Test-Driven Development**: For every new system or feature, create comprehensive unit tests (`gdUnit4`) and ensure all code adheres to `gdformat` and `gdlint --type-check` standards.

---

**4. Important Notes & Considerations**

*   **`main_scene`**: Remember that `project.godot`'s `run/main_scene` is currently set to `test_room.tscn`. This will likely need to be updated or managed as the game's actual main scene develops.
*   **`GDScript Toolkit 4.x`**: This toolkit is listed in `AGENTS.md` but has not been explicitly used or configured yet. Its integration might be a future task if specific functionalities are needed.
*   **`GameState` Instantiation in Tests**: In unit tests, `GameState` needs to be manually instantiated (`GameStateScript.new()`) and `_initialize_state()` called, as Autoloads are not automatically available in the test environment as they are in the running game.

Good luck!