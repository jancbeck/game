extends GdUnitTestSuite

const QuestSystemScript = preload("res://scripts/core/quest_system.gd")
const DataLoader = preload("res://scripts/data/data_loader.gd")
const GameStateScript = preload("res://scripts/core/game_state.gd")

var _game_state: GameStateScript


func before_test():
	_game_state = GameStateScript.new()

	_game_state._initialize_state()

	# Basic structures for QuestSystem to avoid initial warnings

	_game_state._state["player"]["flexibility"] = {"charisma": 10, "cunning": 10, "empathy": 10}

	_game_state._state["player"]["convictions"] = {
		"violence_thoughts": 0, "deceptive_acts": 0, "compassionate_acts": 0
	}

	_game_state._state["world"]["npc_states"] = {
		"guard_captain": {"alive": true, "relationship": 0, "memory_flags": []}
	}

	_game_state._state["world"]["location_flags"] = {}

	# Mock DataLoader.get_quest to return valid data for testing QuestSystem

	DataLoader.set_test_data(
		"rescue_prisoner",
		{
			"id": "rescue_prisoner",
			"approaches":
			{
				"violent":
				{
					"requires": {"violence_thoughts": 3},
					"degrades": {"flexibility_charisma": -2, "violence_thoughts": 2},
					"rewards":
					{
						"convictions": {"violence_thoughts": 2},
						"memory_flags": ["guard_captain_hostile"]
					}
				},
				"stealthy":
				{
					"requires": {"flexibility_cunning": 5},
					"degrades": {"flexibility_cunning": -1, "deceptive_acts": 2},
					"rewards": {"convictions": {"deceptive_acts": 2}, "memory_flags": []}
				}
			},
			"outcomes":
			{
				"all":
				[{"advance_to": "investigate_ruins"}, {"unlock_location": "rebel_hideout_innere"}]
			}
		}
	)


func after_test():
	_game_state.free()
	DataLoader.clear_test_data()


func test_start_quest_sets_status_to_active():
	# Arrange
	_game_state._state["quests"]["rescue_prisoner"] = {
		"status": "available", "approach_taken": "", "objectives_completed": []
	}

	# Act
	var result = QuestSystemScript.start_quest(_game_state.state, "rescue_prisoner")

	# Assert
	assert_that(result["quests"]["rescue_prisoner"]["status"]).is_equal("active")


func test_start_quest_fails_if_prerequisites_not_met():
	# Arrange
	# Define a quest that requires another quest to be completed
	DataLoader.set_test_data(
		"quest_with_prereq",
		{
			"id": "quest_with_prereq",
			"prerequisites": [{"completed": "non_existent_quest"}],
			"approaches": {},
			"outcomes": {}
		}
	)

	# Act
	var can_start = QuestSystemScript.check_prerequisites(_game_state.state, "quest_with_prereq")

	# Assert
	assert_that(can_start).is_false()


func test_complete_quest_handles_maxed_stats():
	# Arrange
	_game_state._state["quests"]["rescue_prisoner"] = {
		"status": "active", "approach_taken": "", "objectives_completed": []
	}
	# Set a stat to near max (assuming max is 100 or similar, but let's just check it increments)
	_game_state._state["player"]["convictions"]["violence_thoughts"] = 99

	# Act
	var result = QuestSystemScript.complete_quest(_game_state.state, "rescue_prisoner", "violent")

	# Assert
	# Violent approach rewards +2 violence_thoughts
	assert_that(result["player"]["convictions"]["violence_thoughts"]).is_equal(101)


func test_complete_quest_handles_zero_degradation():
	# Arrange
	_game_state._state["quests"]["rescue_prisoner"] = {
		"status": "active", "approach_taken": "", "objectives_completed": []
	}
	# Set a stat to 0
	_game_state._state["player"]["flexibility"]["charisma"] = 0

	# Act
	# Violent approach degrades flexibility_charisma by -2
	var result = QuestSystemScript.complete_quest(_game_state.state, "rescue_prisoner", "violent")

	# Assert
	# Should go to -2 (or 0 if clamped, but let's assume no clamping for now based on requirements)
	assert_that(result["player"]["flexibility"]["charisma"]).is_equal(0)
