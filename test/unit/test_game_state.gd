extends GdUnitTestSuite

const PlayerSystemScript = preload("res://scripts/core/player_system.gd")
const GameStateScript = preload("res://scripts/core/game_state.gd")

var _game_state


func before_test():
	_game_state = GameStateScript.new()
	# Manually initialize since we aren't adding to tree to trigger _ready immediately
	_game_state._initialize_state()


func after_test():
	_game_state.free()


func test_initial_state():
	var state = _game_state.state
	assert_that(state["player"]["health"]).is_equal(100)
	assert_that(state["world"]["act"]).is_equal(1)
	assert_that(state["player"]["position"]).is_equal(Vector3.ZERO)


func test_dispatch_updates_state():
	var initial_pos = _game_state.state["player"]["position"]

	# Dispatch a move action
	_game_state.dispatch(func(s): return PlayerSystemScript.move(s, Vector3.FORWARD, 1.0))

	var new_pos = _game_state.state["player"]["position"]
	assert_that(initial_pos).is_not_equal(new_pos)
	# Forward is (0, 0, -1), speed 5.0, delta 1.0 -> (0, 0, -5)
	assert_that(new_pos).is_equal(Vector3(0, 0, -5))


func test_reducer_immutability():  # Test 3a
	var original = {
		"player":
		{
			"position": Vector3.ZERO,
			"health": 100,
			"flexibility": {},
			"convictions": {},
			"inventory": [],
			"equipment": {}
		},
		"world": {},
		"quests": {},
		"dialogue_vars": {},
		"combat": {},
		"meta": {}
	}

	var copy = original.duplicate(true)
	var result = PlayerSystemScript.move(original, Vector3.FORWARD, 1.0)

	assert_that(original).is_equal(copy)


func test_state_encapsulation():  # Test 3b
	var state_ref = _game_state.state
	# Modify the copy we got
	state_ref["player"]["position"] = Vector3(999, 999, 999)

	# Fetch fresh state
	var current_state = _game_state.state

	assert_that(current_state["player"]["position"]).is_not_equal(Vector3(999, 999, 999))
