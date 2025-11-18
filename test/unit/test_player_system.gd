extends GdUnitTestSuite
class_name TestPlayerSystem

var initial_state: Dictionary

func before_test():
    initial_state = {
        "player": {
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
    var direction = Vector3(1, 0, 0) # Move along X-axis
    var delta = 0.5
    var expected_position = Vector3(5 * delta, 0, 0) # speed is 5.0 in PlayerSystem

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
