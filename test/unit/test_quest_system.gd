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
					[
						{"advance_to": "report_to_rebel_leader"},
						{"unlock_location": "rebel_hideout_innere"}
					]
				}
			}
	)


func after_test():
	_game_state.free()
	GdUnit4.restore_class_method(DataLoader, "get_quest")


func test_start_quest_sets_status_to_active():
	# Arrange
	_game_state._state["quests"]["rescue_prisoner"] = {
		"status": "available", "approach_taken": "", "objectives_completed": []
	}

	# Act
	var result = QuestSystemScript.start_quest(_game_state.state, "rescue_prisoner")

	# Assert
	assert_that(result["quests"]["rescue_prisoner"]["status"]).is_equal("active")
