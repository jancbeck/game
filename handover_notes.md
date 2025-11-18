### Handover Notes: Gothic-Inspired Degradation RPG

**Date:** Tuesday, November 18, 2025
**Current Working Directory:** `/Users/jan/workspace/projects/game`

---

**1. Project Status: Core Architecture & Data Pipeline Solidified**

The "Pattern 1: Immutable State Architecture" and "Pattern 2: Character Degradation Engine" are fully implemented and stable. The "Pattern 5: Content-Code Separation" infrastructure is now functional, with `DataLoader` successfully parsing YAML-frontmatter Markdown files for quests.

*   **`scripts/core/game_state.gd`**: Stable singleton for immutable state management.
*   **`scripts/core/player_system.gd`**: Centralized logic for player movement and stat (flexibility/conviction) modification.
*   **`scripts/core/quest_system.gd`**: Logic for completing quests, utilizing `PlayerSystem` for stat changes and `DataLoader` for content. Updated to support memory flags with underscores (e.g., `guard_captain_hostile`).
*   **`scripts/data/data_loader.gd`**: **[STABLE]**
    *   Custom parser implemented to handle YAML frontmatter, including inline lists and dictionaries (e.g., `outcomes: [{...}]`).
    *   Tested and verified with `rescue_prisoner.md`.
*   **`scripts/presentation/player_presentation.gd`**: Minimal presentation layer.
*   **`data/quests/rescue_prisoner.md`**: Validated quest definition file.

---

**2. Validation & Testing**

*   **Unit Tests**: **ALL PASSING** (23/23)
    *   `test/unit/test_game_state.gd`: 4 tests passed.
    *   `test/unit/test_player_system.gd`: 8 tests passed.
    *   `test/unit/test_quest_system.gd`: 9 tests passed.
    *   `test/unit/test_data_loader.gd`: 2 tests passed.
*   **Code Quality**: All scripts formatted with `gdformat` and checked with `gdlint`.

---

**3. Next Steps (Based on AGENTS.md - Phase 1 Deliverables)**

1.  **Implement "Pattern 3: Thoughts → Words → Actions → Character Pipeline"**:
    *   Design and implement the **Internal Monologue System**. This is the next major architectural component.
    *   Create a new system (e.g., `ThoughtSystem`) to handle thought accumulation and triggering.
2.  **Expand Content**:
    *   Add `data/dialogues/*.yarn` parsing support to `DataLoader` (using YarnSpinner-Godot or a custom parser if sticking to the current lightweight approach).
    *   Add `data/characters/*.json` parsing.
3.  **Enhance Presentation**:
    *   Visualize the degradation (color shifts, UI stats) in `player_presentation.gd` or a new UI scene to provide feedback to the player.

---

**4. Important Notes & Considerations**

*   **Data Format**: The `DataLoader` uses a custom, lightweight YAML/JSON-hybrid parser for frontmatter. It supports inline lists `[...]` and inline dicts `{key: val}`, but is not a full YAML parser. Keep data files simple or extend the parser if complexity grows.
*   **Memory Flags**: The convention for memory flags in `QuestSystem` is `NPC_ID_FLAG_NAME`. The parsing logic uses `rsplit("_", true, 1)` to allow `NPC_ID` to contain underscores (e.g., `guard_captain`).
*   **Tests**: Use `source .venv/bin/activate` before running `gdlint` or `gdformat`.

Good luck!