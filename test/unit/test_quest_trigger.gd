class_name TestQuestTrigger
extends GdUnitTestSuite

const QuestTriggerScene = preload("res://scenes/quest_trigger.tscn")
const GameStateScript = preload("res://scripts/core/game_state.gd")
const QuestSystemScript = preload("res://scripts/core/quest_system.gd")
const DataLoader = preload("res://scripts/data/data_loader.gd")

var _game_state_mock: GameStateScript
var _quest_trigger_instance: Area3D


func before_test():
	_game_state_mock = GameStateScript.new()
	_game_state_mock._initialize_state()

	# Ensure the test quest is available
	_game_state_mock._state["quests"]["test_quest"] = {
		"status": "available", "approach_taken": "", "objectives_completed": []
	}

	_quest_trigger_instance = QuestTriggerScene.instantiate()
	_quest_trigger_instance.quest_id = "test_quest"
	add_child(_quest_trigger_instance)


func after_test():
	if _quest_trigger_instance:
		_quest_trigger_instance.queue_free()
	if _game_state_mock:
		_game_state_mock.free()


func test_quest_trigger_starts_and_completes_quest_on_interact():
	# Arrange
	# Simulate player entering range
	_quest_trigger_instance.player_in_range = true

	# Mock DataLoader.get_quest to return valid data for completion
	GdUnit4.replace_class_method(
		DataLoader,
		"get_quest",
		func(quest_id):
			return {
				"id": quest_id,
				"approaches":
				{
					"violent":
					{
						"requires": {},
						"degrades": {},
						"rewards": {"convictions": {}, "memory_flags": {}},
					},
				},
				"outcomes": {"all": []},
			}
	)

	# Act
	# Simulate 'interact' action press
	var event = InputEventKey.new()
	event.set_keycode(KEY_E)
	event.set_pressed(true)
	_quest_trigger_instance._input(event)

	# Assert
	assert_that(_game_state_mock.state["quests"]["test_quest"]["status"]).is_equal("completed")
	assert_that(_game_state_mock.state["quests"]["test_quest"]["approach_taken"]).is_equal(
		"violent"
	)

	# Clean up mock
	GdUnit4.restore_class_method(DataLoader, "get_quest")


func test_quest_trigger_does_not_fire_if_player_not_in_range():
	# Arrange
	_quest_trigger_instance.player_in_range = false

	var initial_state = _game_state_mock.state.duplicate(true)

	# Act
	var event = InputEventKey.new()
	event.set_keycode(KEY_E)
	event.set_pressed(true)
	_quest_trigger_instance._input(event)

	# Assert - state should be unchanged
	assert_that(_game_state_mock.state).is_equal(initial_state)


func test_quest_trigger_removes_itself_after_interaction():
	# Arrange
	_quest_trigger_instance.player_in_range = true

	# Mock DataLoader.get_quest
	GdUnit4.replace_class_method(
		DataLoader,
		"get_quest",
		func(quest_id):
			return {
				"id": quest_id,
				"approaches":
				{
					"violent":
					{
						"requires": {},
						"degrades": {},
						"rewards": {"convictions": {}, "memory_flags": {}}
					}
				},
				"outcomes": {"all": []}
			}
	)

	# Act
	var event = InputEventKey.new()
	event.set_keycode(KEY_E)
	event.set_pressed(true)
	_quest_trigger_instance._input(event)

	# Assert
	assert_that(_quest_trigger_instance.is_queued_for_deletion()).is_true()

	# Clean up mock
	GdUnit4.restore_class_method(DataLoader, "get_quest")
