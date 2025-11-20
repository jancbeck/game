extends GdUnitTestSuite

const QuestSystemScript = preload("res://scripts/core/quest_system.gd")
const DataLoaderScript = preload("res://scripts/data/data_loader.gd")
const GameStateScript = preload("res://scripts/core/game_state.gd") # Load the script to use static/const if needed, but we instance for state

var _initial_state = {
	"quests": {
		"join_rebels": {"status": "available", "approach_taken": "", "objectives_completed": []}
	},
	"player": {
		"flexibility": {"charisma": 10, "cunning": 10, "empathy": 10},
		"convictions": {}
	},
	"world": {"npc_states": {}, "location_flags": {}, "memory_flags": []}
}

func before_test():
	# Mock quest data - WE MUST MATCH THE FILE CHANGE TO PASS IF WE WERE MOCKING EXACTLY,
	# BUT here we are testing logic. 
	# Actually, to verify the *file change* works, we should rely on the real file loader or update the mock to match.
	# The user request is about visual feedback in game.
	# But I should add a test ensuring that completing this quest actually degrades stats now.
	pass

func after_test():
	DataLoaderScript.clear_test_data()

func test_join_rebels_diplomatic_degrades_charisma():
	var state = _initial_state.duplicate(true)
	
	# Ensure we are using the REAL data file for this test to verify the configuration
	# DataLoader defaults to loading from file if not in test_data
	# So we ensure test_data is clear for this quest
	
	# 1. Start quest
	state = QuestSystemScript.start_quest(state, "join_rebels")
	
	# 2. Complete with diplomatic
	state = QuestSystemScript.complete_quest(state, "join_rebels", "diplomatic")
	
	# 3. Assert degradation
	# We set it to -5 in the file
	assert_that(state["player"]["flexibility"]["charisma"]).is_equal(5)
	assert_that(state["player"]["flexibility"]["empathy"]).is_equal(8)
