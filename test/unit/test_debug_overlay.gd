class_name TestDebugOverlay
extends GdUnitTestSuite

const DebugOverlayScene = preload("res://scenes/ui/debug_overlay.tscn")
const GameStateScript = preload("res://scripts/core/game_state.gd")

var _game_state_mock: GameStateScript
var _debug_overlay_instance: CanvasLayer
var _mock_state: Dictionary


func before_test():
	_game_state_mock = GameStateScript.new()
	_game_state_mock._initialize_state()
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
	if _game_state_mock:
		_game_state_mock.free()


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
	# Arrange: GameState.state is initially set by _initialize_state
	_game_state_mock._state["player"]["flexibility"] = {
		"charisma": 10, "cunning": 10, "empathy": 10
	}
	_game_state_mock._state["player"]["convictions"] = {
		"violence_thoughts": 0, "deceptive_acts": 0, "compassionate_acts": 0
	}

	var expected_flexibility_str = JSON.stringify(
		_game_state_mock._state["player"]["flexibility"], "\t", true
	)
	var expected_convictions_str = JSON.stringify(
		_game_state_mock._state["player"]["convictions"], "\t", true
	)
	var expected_text = (
		"Flexibility:\n"
		+ expected_flexibility_str
		+ "\n\nConvictions:\n"
		+ expected_convictions_str
	)

	# Act: The _ready() function (called automatically by the test runner) connects and calls _on_state_changed immediately.
	# We need to ensure that the GameState's initial state is set BEFORE _debug_overlay_instance is instantiated.
	# Since _debug_overlay_instance is instantiated in before_test(), we can't set _game_state_mock._state here
	# without it being too late for _ready().
	# Therefore, we will simulate the _ready() call, but only connect if not already connected

	# _ready() is called automatically by the test runner when the scene is instantiated in before_test().
	# The initial state is already set by _game_state_mock._initialize_state() in before_test(), and _ready() connects to it.

	# Assert
	assert_that(_debug_overlay_instance.get_node("RichTextLabel").text).is_equal(expected_text)
