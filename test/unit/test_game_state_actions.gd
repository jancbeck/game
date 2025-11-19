class_name TestGameStateActions
extends GdUnitTestSuite

const GameStateScript = preload("res://scripts/core/game_state.gd")
const QuestSystemScript = preload("res://scripts/core/quest_system.gd")
const DataLoader = preload("res://scripts/data/data_loader.gd")

var _game_state_instance: GameStateScript


func before_test():
	_game_state_instance = GameStateScript.new()
	_game_state_instance._initialize_state()
	# Replace the autoload with our test instance for GameStateActions
	Engine.unregister_singleton("GameState")
	Engine.register_singleton("GameState", _game_state_instance)


func after_test():
	# Restore autoload
	Engine.unregister_singleton("GameState")
	if _game_state_instance:
		_game_state_instance.free()
	DataLoader.clear_test_data()


func test_modify_conviction_changes_player_state():
	# Arrange
	var initial = _game_state_instance.state["player"]["convictions"]["violence_thoughts"]
	
	# Act
	GameStateActions.modify_conviction("violence_thoughts", 2)
	
	# Assert
	var updated = _game_state_instance.state["player"]["convictions"]["violence_thoughts"]
	assert_that(updated).is_equal(initial + 2)
	# Verify other state not dropped
	assert_that(_game_state_instance.state["player"]["convictions"]["compassionate_acts"]).is_not_null()


func test_modify_flexibility_changes_player_state():
	# Arrange
	var initial = _game_state_instance.state["player"]["flexibility"]["charisma"]
	
	# Act
	GameStateActions.modify_flexibility("charisma", -3)
	
	# Assert
	var updated = _game_state_instance.state["player"]["flexibility"]["charisma"]
	assert_that(updated).is_equal(initial - 3)
	# Verify other state not dropped
	assert_that(_game_state_instance.state["player"]["flexibility"]["cunning"]).is_not_null()


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
	
	_game_state_instance.dispatch(func(state): return QuestSystemScript.start_quest(state, "join_rebels"))
	_game_state_instance.dispatch(func(state): return QuestSystemScript.complete_quest(state, "join_rebels", "diplomatic"))
	
	# Assert - Quest B now available
	assert_that(GameStateActions.can_start_quest("rescue_prisoner")).is_true()
