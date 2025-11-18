extends GdUnitTestSuite

const QuestSystemScript = preload("res://scripts/core/quest_system.gd")
const DataLoader = preload("res://scripts/data/data_loader.gd")  # For dummy data
const GameStateScript = preload("res://scripts/core/game_state.gd")

var _game_state: GameStateScript


func before_test():
	_game_state = GameStateScript.new()
	_game_state._initialize_state()
	# Basic structures for QuestSystem to avoid initial warnings
	_game_state._state["player"]["flexibility"] = {"charisma": 10, "cunning": 10, "empathy": 10}
	_game_state._state["player"]["convictions"] = {
		"violence_thoughts": 0,
		"deceptive_acts": 0,
		"compassionate_acts": 0,
		# Added for stealthy approach test
		"cunning": 0
	}
	_game_state._state["world"]["npc_states"] = {
		"guard": {"alive": true, "relationship": 0, "memory_flags": []}
	}
	_game_state._state["world"]["location_flags"] = {}


func test_violent_approach_degrades_charisma_and_adds_conviction():
	# Arrange
	_game_state._state["quests"]["rescue_prisoner"] = {
		"status": "active", "approach_taken": "", "objectives_completed": []
	}
	_game_state._state["quests"]["joined_rebels"] = {
		"status": "completed", "approach_taken": "", "objectives_completed": []
	}  # Prerequisite for rescue_prisoner

	# Act
	var result = QuestSystemScript.complete_quest(_game_state.state, "rescue_prisoner", "violent")

	# Assert
	assert_that(result["player"]["flexibility"]["charisma"]).is_equal(8)  # 10 - 2
	assert_that(result["player"]["convictions"]["violence_thoughts"]).is_equal(2)  # 0 + 2


func test_stealthy_approach_degrades_cunning_and_adds_conviction():
	# Arrange
	_game_state._state["quests"]["rescue_prisoner"] = {
		"status": "active", "approach_taken": "", "objectives_completed": []
	}
	_game_state._state["quests"]["joined_rebels"] = {
		"status": "completed", "approach_taken": "", "objectives_completed": []
	}  # Prerequisite for rescue_prisoner
	_game_state._state["player"]["flexibility"]["cunning"] = 10

	# Act
	var result = QuestSystemScript.complete_quest(_game_state.state, "rescue_prisoner", "stealthy")

	# Assert
	assert_that(result["player"]["flexibility"]["cunning"]).is_equal(9)  # 10 - 1
	assert_that(result["player"]["convictions"]["cunning"]).is_equal(1)  # 0 + 1


func test_memory_flags_set_correctly_for_violent_approach():
	# Arrange
	_game_state._state["quests"]["rescue_prisoner"] = {
		"status": "active", "approach_taken": "", "objectives_completed": []
	}
	_game_state._state["quests"]["joined_rebels"] = {
		"status": "completed", "approach_taken": "", "objectives_completed": []
	}  # Prerequisite for rescue_prisoner

	# Act
	var result = QuestSystemScript.complete_quest(_game_state.state, "rescue_prisoner", "violent")

	# Assert
	assert_that(result["world"]["npc_states"]["guard"]["memory_flags"]).contains("hostile")


func test_cannot_complete_non_existent_quest():
	# Arrange
	_game_state._state["quests"]["rescue_prisoner"] = {
		"status": "active", "approach_taken": "", "objectives_completed": []
	}
	_game_state._state["quests"]["joined_rebels"] = {
		"status": "completed", "approach_taken": "", "objectives_completed": []
	}  # Prerequisite for rescue_prisoner

	# Act
	var result = QuestSystemScript.complete_quest(
		_game_state.state, "non_existent_quest", "violent"
	)

	# Assert - state should be unchanged
	assert_that(result).is_equal(_game_state.state)


func test_cannot_complete_inactive_quest():
	# Arrange
	_game_state._state["quests"]["rescue_prisoner"] = {
		"status": "completed", "approach_taken": "", "objectives_completed": []  # Already completed
	}
	_game_state._state["quests"]["joined_rebels"] = {
		"status": "completed", "approach_taken": "", "objectives_completed": []
	}  # Prerequisite for rescue_prisoner

	# Act
	var result = QuestSystemScript.complete_quest(_game_state.state, "rescue_prisoner", "violent")

	# Assert - state should be unchanged
	assert_that(result).is_equal(_game_state.state)


func test_unlocks_follow_up_quest():
	# Arrange
	_game_state._state["quests"]["rescue_prisoner"] = {
		"status": "active", "approach_taken": "", "objectives_completed": []
	}
	_game_state._state["quests"]["joined_rebels"] = {
		"status": "completed", "approach_taken": "", "objectives_completed": []
	}  # Prerequisite for rescue_prisoner
	# Ensure the follow-up quest is not already in the initial state
	_game_state._state["quests"].erase("report_to_rebel_leader")

	# Act
	var result = QuestSystemScript.complete_quest(_game_state.state, "rescue_prisoner", "violent")

	# Assert
	assert_that(result["quests"].has("report_to_rebel_leader")).is_true()
	assert_that(result["quests"]["report_to_rebel_leader"]["status"]).is_equal("available")


func test_state_immutability():
	# Arrange
	_game_state._state["quests"]["rescue_prisoner"] = {
		"status": "active", "approach_taken": "", "objectives_completed": []
	}
	_game_state._state["quests"]["joined_rebels"] = {
		"status": "completed", "approach_taken": "", "objectives_completed": []
	}  # Prerequisite for rescue_prisoner
	# Create a deep copy of the initial state to compare against later
	var initial_state_copy = _game_state.state.duplicate(true)

	# Act
	QuestSystemScript.complete_quest(_game_state.state, "rescue_prisoner", "violent")

	# Assert: The original _game_state.state should not have been modified
	assert_that(_game_state.state).is_equal(initial_state_copy)


func test_unlocks_location():
	# Arrange
	_game_state._state["quests"]["rescue_prisoner"] = {
		"status": "active", "approach_taken": "", "objectives_completed": []
	}
	_game_state._state["quests"]["joined_rebels"] = {
		"status": "completed", "approach_taken": "", "objectives_completed": []
	}  # Prerequisite for rescue_prisoner

	# Act
	var result = QuestSystemScript.complete_quest(_game_state.state, "rescue_prisoner", "violent")

	# Assert
	assert_that(result["world"]["location_flags"]).contains_keys(["rebel_hideout_innere"])
	assert_that(result["world"]["location_flags"]["rebel_hideout_innere"]).is_true()


func test_does_not_unlock_already_existing_next_quest():
	# Arrange
	_game_state._state["quests"]["rescue_prisoner"] = {
		"status": "active", "approach_taken": "", "objectives_completed": []
	}
	_game_state._state["quests"]["joined_rebels"] = {
		"status": "completed", "approach_taken": "", "objectives_completed": []
	}  # Prerequisite for rescue_prisoner
	# Ensure the follow-up quest is already in the initial state
	_game_state._state["quests"]["report_to_rebel_leader"] = {
		"status": "available", "approach_taken": "", "objectives_completed": []
	}

	# Act
	var result = QuestSystemScript.complete_quest(_game_state.state, "rescue_prisoner", "violent")

	# Assert

	assert_that(result["quests"].has("report_to_rebel_leader")).is_true()

	# Should not change status or re-add

	assert_that(result["quests"]["report_to_rebel_leader"]["status"]).is_equal("available")


func after_test():
	_game_state.free()
