class_name TestDebugOverlay
extends GdUnitTestSuite

const DebugOverlayScene = preload("res://scenes/ui/debug_overlay.tscn")
const GameStateScript = preload("res://scripts/core/game_state.gd")

var _debug_overlay_instance: CanvasLayer
var _original_global_state: Dictionary


func before_test():
	# Save global state to restore later
	_original_global_state = GameState.state.duplicate(true)

	# Reset global state to a known clean state for testing
	GameState._initialize_state()
	# Ensure specific values expected by tests
	GameState._state["player"]["flexibility"] = {"charisma": 10, "cunning": 10, "empathy": 10}
	GameState._state["player"]["convictions"] = {"violence_thoughts": 0, "deceptive_acts": 0, "compassionate_acts": 0}

	_debug_overlay_instance = DebugOverlayScene.instantiate()
	add_child(_debug_overlay_instance)


func after_test():
	if _debug_overlay_instance:
		_debug_overlay_instance.queue_free()

	# Restore global state
	GameState._state = _original_global_state


func test_debug_overlay_updates_label_on_state_change():
	# Arrange
	var test_state = GameState.state.duplicate(true)
	test_state["player"]["flexibility"] = {"charisma": 7, "cunning": 5, "empathy": 8}
	test_state["player"]["convictions"] = {"violence_thoughts": 10, "deceptive_acts": 5, "compassionate_acts": 15}

	# Act
	_debug_overlay_instance._update_display(test_state)

	# Assert - Check that the text contains the expected state information
	# (debug controls are also included now)
	var actual_text = _debug_overlay_instance.get_node("RichTextLabel").text
	assert_that(actual_text).contains("Flexibility:")
	assert_that(actual_text).contains("Convictions:")


func test_debug_overlay_initial_state_update():
	# Arrange
	# State is already set in before_test, and DebugOverlay should have read it in _ready

	# Assert - Check that initial state is displayed (with debug controls appended)
	var actual_text = _debug_overlay_instance.get_node("RichTextLabel").text
	assert_that(actual_text).contains("Flexibility:")
	assert_that(actual_text).contains("Convictions:")
	assert_that(actual_text).contains("[DEBUG CONTROLS]")


func test_format_log_message_quest_timeline_started():
	# Arrange
	var log = {
		"event": "quest_timeline_started",
		"details": {"quest_id": "join_rebels"}
	}

	# Act
	var formatted = _debug_overlay_instance._format_log_message(log)

	# Assert - Should display quest name, not raw event
	assert_that(formatted).is_equal("Started: join_rebels")


func test_format_log_message_other_event_types():
	# Arrange
	var log = {
		"event": "quest_trigger_initialized",
		"details": {"quest_id": "some_quest"}
	}

	# Act
	var formatted = _debug_overlay_instance._format_log_message(log)

	# Assert - Should display raw event for non-special types
	assert_that(formatted).is_equal("quest_trigger_initialized")
