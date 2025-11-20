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
