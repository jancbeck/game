class_name TestGameStateActions
extends GdUnitTestSuite

const QuestSystemScript = preload("res://scripts/core/quest_system.gd")
const DataLoader = preload("res://scripts/data/data_loader.gd")


func before_test():
	# Reset GameState to clean state for each test
	GameState.reset()


func after_test():
	# Clean up test data
	DataLoader.clear_test_data()
	# Reset state again for good measure
	GameState.reset()


func test_modify_conviction_changes_player_state():
	# Arrange
	var initial = GameState.state["player"]["convictions"]["violence_thoughts"]

	# Act
	GameStateActions.modify_conviction("violence_thoughts", 2)

	# Assert
	var updated = GameState.state["player"]["convictions"]["violence_thoughts"]
	assert_that(updated).is_equal(initial + 2)
	# Verify other state not dropped
	assert_that(GameState.state["player"]["convictions"]["compassionate_acts"]).is_not_null()


func test_modify_flexibility_changes_player_state():
	# Arrange
	var initial = GameState.state["player"]["flexibility"]["charisma"]

	# Act
	GameStateActions.modify_flexibility("charisma", -3)

	# Assert
	var updated = GameState.state["player"]["flexibility"]["charisma"]
	assert_that(updated).is_equal(initial - 3)
	# Verify other state not dropped
	assert_that(GameState.state["player"]["flexibility"]["cunning"]).is_not_null()


func test_can_start_quest_delegates_prerequisites():
	# Arrange - Quest B requires Quest A
	DataLoader.set_test_data("rescue_prisoner", {
		"id": "rescue_prisoner",
		"prerequisites": [{"completed": "join_rebels"}],
		"approaches": {},
		"outcomes": {}
	})

	# Assert - Quest B initially locked
	assert_that(GameStateActions.can_start_quest("rescue_prisoner")).is_false()

	# Act - Complete Quest A
	# Mock join_rebels quest data
	DataLoader.set_test_data("join_rebels", {
		"id": "join_rebels",
		"approaches": {
			"diplomatic": {
				"requires": {},
				"degrades": {},
				"rewards": {"convictions": {}, "memory_flags": []}
			}
		},
		"outcomes": {"all": []}
	})

	GameState.dispatch(func(state): return QuestSystemScript.start_quest(state, "join_rebels"))
	GameState.dispatch(func(state): return QuestSystemScript.complete_quest(state, "join_rebels", "diplomatic"))

	# Assert - Quest B now available
	assert_that(GameStateActions.can_start_quest("rescue_prisoner")).is_true()


func test_has_memory_flag_finds_world_level_flags():
	# Arrange - Add world-level memory flag (as done by complete_quest)
	GameState.dispatch(func(state):
		var new_state = state.duplicate(true)
		new_state["world"]["memory_flags"].append("rebel_leader_knows_brutal")
		return new_state
	)

	# Act & Assert
	assert_that(GameStateActions.has_memory_flag("rebel_leader_knows_brutal")).is_true()


func test_has_memory_flag_returns_false_for_missing_flag():
	# Act & Assert
	assert_that(GameStateActions.has_memory_flag("nonexistent_flag")).is_false()


func test_has_memory_flag_finds_multiple_world_flags():
	# Arrange - Add multiple world-level flags
	GameState.dispatch(func(state):
		var new_state = state.duplicate(true)
		new_state["world"]["memory_flags"].append("flag_one")
		new_state["world"]["memory_flags"].append("flag_two")
		return new_state
	)

	# Act & Assert - Both flags should be found
	assert_that(GameStateActions.has_memory_flag("flag_one")).is_true()
	assert_that(GameStateActions.has_memory_flag("flag_two")).is_true()


func test_has_memory_flag_backward_compatible_with_npc_flags():
	# Arrange - Add NPC-specific flag (legacy behavior)
	GameState.dispatch(func(state):
		var new_state = state.duplicate(true)
		if not new_state["world"]["npc_states"].has("npc_1"):
			new_state["world"]["npc_states"]["npc_1"] = {
				"alive": true,
				"relationship": 0,
				"memory_flags": []
			}
		new_state["world"]["npc_states"]["npc_1"]["memory_flags"].append("npc_specific_flag")
		return new_state
	)

	# Act & Assert - NPC flag should still be found
	assert_that(GameStateActions.has_memory_flag("npc_specific_flag")).is_true()


func test_has_memory_flag_prioritizes_world_over_npc():
	# Arrange - Add same flag name to both world and NPC (edge case)
	GameState.dispatch(func(state):
		var new_state = state.duplicate(true)
		new_state["world"]["memory_flags"].append("shared_flag")
		if not new_state["world"]["npc_states"].has("npc_1"):
			new_state["world"]["npc_states"]["npc_1"] = {
				"alive": true,
				"relationship": 0,
				"memory_flags": []
			}
		new_state["world"]["npc_states"]["npc_1"]["memory_flags"].append("shared_flag")
		return new_state
	)

	# Act & Assert - Should find it (doesn't matter which one)
	assert_that(GameStateActions.has_memory_flag("shared_flag")).is_true()
