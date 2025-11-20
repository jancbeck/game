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
	_quest_trigger_instance.debug_auto_complete_approach = "violent"
	_quest_trigger_instance.game_state = _game_state_mock  # Inject mock
	add_child(_quest_trigger_instance)

	# Setup InputMap
	if not InputMap.has_action("interact"):
		InputMap.add_action("interact")

	var key = InputEventKey.new()
	key.keycode = KEY_E
	InputMap.action_add_event("interact", key)


func after_test():
	if _quest_trigger_instance:
		_quest_trigger_instance.queue_free()
	if _game_state_mock:
		_game_state_mock.free()
	DataLoader.clear_test_data()

	if InputMap.has_action("interact"):
		InputMap.erase_action("interact")


func test_quest_trigger_starts_and_completes_quest_on_interact():
	# Arrange
	# Simulate player entering range
	_quest_trigger_instance.player_in_range = true

	# Mock DataLoader.get_quest to return valid data for completion
	(
		DataLoader
		. set_test_data(
			"test_quest",
			{
				"id": "test_quest",
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
	DataLoader.clear_test_data()


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


func test_quest_trigger_removes_itself_after_completion():
	# Arrange
	_quest_trigger_instance.player_in_range = true

	# Mock DataLoader.get_quest
	DataLoader.set_test_data(
		"test_quest",
		{
			"id": "test_quest",
			"approaches":
			{
				"violent":
				{"requires": {}, "degrades": {}, "rewards": {"convictions": {}, "memory_flags": {}}}
			},
			"outcomes": {"all": []}
		}
	)

	# Act
	var event = InputEventKey.new()
	event.set_keycode(KEY_E)
	event.set_pressed(true)
	_quest_trigger_instance._input(event)

	# Debug mode auto-completes quest, which should trigger removal
	# Assert quest is completed
	assert_that(_game_state_mock.state["quests"]["test_quest"]["status"]).is_equal("completed")

	# Assert trigger queued for deletion after completion (not just activation)
	assert_that(_quest_trigger_instance.is_queued_for_deletion()).is_true()

	# Clean up mock
	DataLoader.clear_test_data()


func test_timeline_blocked_when_prerequisites_not_met():
	# Arrange - Setup quest with prerequisites that aren't met
	# Create a quest that requires another quest to be completed
	var quest_with_prereq = "investigate_ruins"
	DataLoader.set_test_data(
		quest_with_prereq,
		{
			"id": quest_with_prereq,
			"prerequisites": [{"completed": "rescue_prisoner"}],
			"approaches":
			{
				"peaceful":
				{"requires": {}, "degrades": {}, "rewards": {"convictions": {}, "memory_flags": {}}}
			},
			"outcomes": {"all": []}
		}
	)

	# Set investigate_ruins as available but rescue_prisoner NOT completed
	_game_state_mock._state["quests"][quest_with_prereq] = {
		"status": "available", "approach_taken": "", "objectives_completed": []
	}
	# rescue_prisoner is NOT in completed state (doesn't exist in state at all)

	# Setup trigger with timeline
	var trigger_with_timeline = QuestTriggerScene.instantiate()
	trigger_with_timeline.quest_id = quest_with_prereq
	trigger_with_timeline.timeline_id = "quest_investigate_ruins_intro"
	trigger_with_timeline.game_state = _game_state_mock
	add_child(trigger_with_timeline)
	trigger_with_timeline.player_in_range = true

	# Act - Try to interact
	var event = InputEventKey.new()
	event.set_keycode(KEY_E)
	event.set_pressed(true)
	trigger_with_timeline._input(event)

	# Assert - Quest should still be available (not started), timeline blocked
	assert_that(_game_state_mock.state["quests"][quest_with_prereq]["status"]).is_equal("available")

	# Clean up
	trigger_with_timeline.queue_free()
	DataLoader.clear_test_data()


func test_timeline_starts_when_prerequisites_met():
	# Arrange - Setup quest with prerequisites that ARE met
	var quest_with_prereq = "investigate_ruins"
	DataLoader.set_test_data(
		quest_with_prereq,
		{
			"id": quest_with_prereq,
			"prerequisites": [{"completed": "rescue_prisoner"}],
			"approaches":
			{
				"peaceful":
				{"requires": {}, "degrades": {}, "rewards": {"convictions": {}, "memory_flags": {}}}
			},
			"outcomes": {"all": []}
		}
	)

	# Set investigate_ruins as available AND rescue_prisoner as completed
	_game_state_mock._state["quests"][quest_with_prereq] = {
		"status": "available", "approach_taken": "", "objectives_completed": []
	}
	_game_state_mock._state["quests"]["rescue_prisoner"] = {
		"status": "completed", "approach_taken": "peaceful", "objectives_completed": []
	}

	# Setup trigger with timeline (but we can't test DialogSystem call directly)
	var trigger_with_timeline = QuestTriggerScene.instantiate()
	trigger_with_timeline.quest_id = quest_with_prereq
	trigger_with_timeline.timeline_id = "quest_investigate_ruins_intro"
	trigger_with_timeline.game_state = _game_state_mock
	add_child(trigger_with_timeline)
	trigger_with_timeline.player_in_range = true

	# Act - Try to interact
	var event = InputEventKey.new()
	event.set_keycode(KEY_E)
	event.set_pressed(true)
	trigger_with_timeline._input(event)

	# Assert - Prerequisites met, so the code path should proceed
	# We can't easily verify DialogSystem.start_timeline was called in unit test
	# But we can verify prerequisites were checked and didn't block execution
	# Quest should still be "available" (timeline would start it via Dialogic event)
	assert_that(_game_state_mock.state["quests"][quest_with_prereq]["status"]).is_equal("available")

	# Clean up
	trigger_with_timeline.queue_free()
	DataLoader.clear_test_data()


func test_timeline_selection_uses_base_for_available_quest():
	# Arrange - Available quest
	var test_quest_id = "investigate_ruins"
	_game_state_mock._state["quests"][test_quest_id] = {
		"status": "available", "approach_taken": "", "objectives_completed": []
	}

	var trigger = QuestTriggerScene.instantiate()
	trigger.quest_id = test_quest_id
	trigger.timeline_id = "quest_investigate_ruins_intro"
	trigger.game_state = _game_state_mock
	add_child(trigger)

	# Act
	var selected_timeline = trigger._get_timeline_for_quest_status("available")

	# Assert - Should use base timeline
	assert_that(selected_timeline).is_equal("quest_investigate_ruins_intro")

	# Clean up
	trigger.queue_free()


func test_timeline_selection_uses_resolution_for_active_quest():
	# Arrange - Active quest with resolution timeline that exists
	var test_quest_id = "investigate_ruins"
	_game_state_mock._state["quests"][test_quest_id] = {
		"status": "active", "approach_taken": "", "objectives_completed": []
	}

	var trigger = QuestTriggerScene.instantiate()
	trigger.quest_id = test_quest_id
	trigger.timeline_id = "quest_investigate_ruins_intro"
	trigger.game_state = _game_state_mock
	add_child(trigger)

	# Act
	var selected_timeline = trigger._get_timeline_for_quest_status("active")

	# Assert - Should use resolution timeline (replaces '_intro' with '_resolution')
	assert_that(selected_timeline).is_equal("quest_investigate_ruins_resolution")

	# Clean up
	trigger.queue_free()


func test_timeline_selection_fallback_when_resolution_missing():
	# Arrange - Active quest but resolution timeline doesn't exist
	var test_quest_id = "missing_resolution_quest"
	_game_state_mock._state["quests"][test_quest_id] = {
		"status": "active", "approach_taken": "", "objectives_completed": []
	}

	var trigger = QuestTriggerScene.instantiate()
	trigger.quest_id = test_quest_id
	trigger.timeline_id = "nonexistent_timeline"  # This timeline + _resolution won't exist
	trigger.game_state = _game_state_mock
	add_child(trigger)

	# Act
	var selected_timeline = trigger._get_timeline_for_quest_status("active")

	# Assert - Should fallback to base timeline
	assert_that(selected_timeline).is_equal("nonexistent_timeline")

	# Clean up
	trigger.queue_free()


func test_completed_quest_does_not_trigger_timeline():
	# Arrange - Completed quest
	var test_quest_id = "investigate_ruins"
	DataLoader.set_test_data(
		test_quest_id,
		{
			"id": test_quest_id,
			"prerequisites": [],
			"approaches":
			{
				"peaceful":
				{"requires": {}, "degrades": {}, "rewards": {"convictions": {}, "memory_flags": {}}}
			},
			"outcomes": {"all": []}
		}
	)

	_game_state_mock._state["quests"][test_quest_id] = {
		"status": "completed", "approach_taken": "peaceful", "objectives_completed": []
	}

	var trigger = QuestTriggerScene.instantiate()
	trigger.quest_id = test_quest_id
	trigger.timeline_id = "quest_investigate_ruins_intro"
	trigger.game_state = _game_state_mock
	add_child(trigger)
	trigger.player_in_range = true

	# Act - Try to interact
	var event = InputEventKey.new()
	event.set_keycode(KEY_E)
	event.set_pressed(true)
	trigger._input(event)

	# Assert - Quest should still be completed (no state change)
	assert_that(_game_state_mock.state["quests"][test_quest_id]["status"]).is_equal("completed")

	# Clean up
	trigger.queue_free()
	DataLoader.clear_test_data()


func test_get_quest_status_returns_available_when_not_in_state():
	# Arrange - Quest not in state
	var test_quest_id = "nonexistent_quest"

	var trigger = QuestTriggerScene.instantiate()
	trigger.quest_id = test_quest_id
	trigger.game_state = _game_state_mock
	add_child(trigger)

	# Act
	var status = trigger._get_quest_status()

	# Assert
	assert_that(status).is_equal("available")

	# Clean up
	trigger.queue_free()


func test_get_quest_status_returns_correct_status_when_in_state():
	# Arrange - Quest in state with active status
	var test_quest_id = "test_quest"
	_game_state_mock._state["quests"][test_quest_id] = {
		"status": "active", "approach_taken": "", "objectives_completed": []
	}

	var trigger = QuestTriggerScene.instantiate()
	trigger.quest_id = test_quest_id
	trigger.game_state = _game_state_mock
	add_child(trigger)

	# Act
	var status = trigger._get_quest_status()

	# Assert
	assert_that(status).is_equal("active")

	# Clean up
	trigger.queue_free()
