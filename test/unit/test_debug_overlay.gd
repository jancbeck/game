class_name TestDebugOverlay
extends GdUnitTestSuite

const DebugOverlayScene = preload("res://scenes/ui/debug_overlay.tscn")
const GameStateScript = preload("res://scripts/core/game_state.gd")

var _debug_overlay_instance: CanvasLayer
var _mock_state: Dictionary
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

	_mock_state = {
		"player":
		{
			"flexibility": {"charisma": 7, "cunning": 5, "empathy": 8},
			"convictions": {"violence_thoughts": 10, "deceptive_acts": 5, "compassionate_acts": 15}
		}
	}


func after_test():
	if _debug_overlay_instance:
		_debug_overlay_instance.queue_free()
	
	# Restore global state
	GameState._state = _original_global_state


func test_debug_overlay_updates_label_on_state_change():
	# Arrange
	var expected_flexibility_str = JSON.stringify(_mock_state["player"]["flexibility"], "\t", true)
	var expected_convictions_str = JSON.stringify(_mock_state["player"]["convictions"], "\t", true)
	var expected_text = (
		"Flexibility:\n"
		+ expected_flexibility_str
		+ "\n\nConvictions:\n"
		+ expected_convictions_str
	)

	# Act
	_debug_overlay_instance.get_node("RichTextLabel").text = ""
	_debug_overlay_instance._on_state_changed(_mock_state)

	# Assert
	assert_that(_debug_overlay_instance.get_node("RichTextLabel").text).is_equal(expected_text)


func test_debug_overlay_initial_state_update():
	# Arrange
	# State is already set in before_test, and DebugOverlay should have read it in _ready
	
	var expected_flexibility_str = JSON.stringify(
		GameState._state["player"]["flexibility"], "\t", true
	)
	var expected_convictions_str = JSON.stringify(
		GameState._state["player"]["convictions"], "\t", true
	)
	var expected_text = (
		"Flexibility:\n"
		+ expected_flexibility_str
		+ "\n\nConvictions:\n"
		+ expected_convictions_str
	)

	# Assert
	assert_that(_debug_overlay_instance.get_node("RichTextLabel").text).is_equal(expected_text)
