class_name TestPlayerSystem
extends GdUnitTestSuite

var initial_state: Dictionary


func before_test():
	initial_state = {
		"player":
		{
			"position": Vector3.ZERO,
			"health": 100,
			"max_health": 100,
			"flexibility": {"charisma": 10, "cunning": 10, "empathy": 10},
			"convictions": {"violence_thoughts": 0, "deceptive_acts": 0, "compassionate_acts": 0},
			"inventory": [],
			"equipment": {"weapon": "", "armor": ""}
		},
		"world": {},
		"quests": {},
		"dialogue_vars": {},
		"combat": {},
		"meta": {}
	}


func test_move_updates_player_position():
	# Arrange
	var direction = Vector3(1, 0, 0)  # Move along X-axis
	var delta = 0.5
	var expected_position = Vector3(5 * delta, 0, 0)  # speed is 5.0 in PlayerSystem

	# Act
	var new_state = PlayerSystem.move(initial_state, direction, delta)

	# Assert
	var actual_position: Vector3 = new_state["player"]["position"]
	assert_that(actual_position).is_equal(expected_position)


func test_move_is_immutable():
	# Arrange
	var direction = Vector3(0, 0, 1)
	var delta = 1.0

	# Act
	var new_state = PlayerSystem.move(initial_state, direction, delta)

	# Assert
	assert_that(new_state).is_not_equal(initial_state)
	var original_position: Vector3 = initial_state["player"]["position"]
	assert_that(original_position).is_equal(Vector3.ZERO)


func test_modify_flexibility_decreases_stat():
	# Act
	var new_state = PlayerSystem.modify_flexibility(initial_state, "charisma", -2)

	# Assert
	assert_that(new_state["player"]["flexibility"]["charisma"]).is_equal(8)


func test_modify_flexibility_clamps_min_max():
	# Arrange
	# Create state where charisma is 1
	var low_state = initial_state.duplicate(true)
	low_state["player"]["flexibility"]["charisma"] = 1

	# Act - try to reduce by 5 (should stop at 0)
	var clamped_low = PlayerSystem.modify_flexibility(low_state, "charisma", -5)

	# Act - try to increase by 5 (should stop at 10)
	var clamped_high = PlayerSystem.modify_flexibility(initial_state, "charisma", 5)

	# Assert
	assert_that(clamped_low["player"]["flexibility"]["charisma"]).is_equal(0)
	assert_that(clamped_high["player"]["flexibility"]["charisma"]).is_equal(10)


func test_modify_flexibility_handles_invalid_stat():
	# Act
	var new_state = PlayerSystem.modify_flexibility(initial_state, "non_existent", -1)

	# Assert
	# Should return state unchanged (maybe with a warning, but we check state here)
	assert_that(new_state).is_equal(initial_state)


func test_modify_conviction_increases_stat():
	# Act
	var new_state = PlayerSystem.modify_conviction(initial_state, "violence_thoughts", 2)

	# Assert
	assert_that(new_state["player"]["convictions"]["violence_thoughts"]).is_equal(2)


func test_modify_conviction_clamps_min_zero():
	# Arrange
	var initial_val = 0

	# Act
	var new_state = PlayerSystem.modify_conviction(initial_state, "violence_thoughts", -5)

	# Assert
	assert_that(new_state["player"]["convictions"]["violence_thoughts"]).is_equal(0)


func test_modify_conviction_handles_invalid_stat():
	# Act
	var new_state = PlayerSystem.modify_conviction(initial_state, "non_existent", 1)

	# Assert
	assert_that(new_state).is_equal(initial_state)
