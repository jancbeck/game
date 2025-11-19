extends GdUnitTestSuite

const ThoughtSystemScript = preload("res://scripts/core/thought_system.gd")
const DataLoaderScript = preload("res://scripts/data/data_loader.gd")

var _initial_state = {
	"player": {"convictions": {"violence_thoughts": 0, "compassionate_acts": 0}},
	"meta": {}
}

func before_test():
	# Mock thought data
	DataLoaderScript.set_test_data("test_thought", {
		"id": "test_thought",
		"trigger": "test_trigger",
		"prompt": "Test Prompt",
		"options": [
			{
				"text": "Option 1",
				"convictions": {"violence_thoughts": 2}
			},
			{
				"text": "Option 2",
				"convictions": {"violence_thoughts": -1}
			}
		]
	})

func after_test():
	DataLoaderScript.clear_test_data()

func test_thought_data_loads_correctly():
	var data = DataLoaderScript.get_thought("test_thought")
	assert_that(data["id"]).is_equal("test_thought")
	assert_that(data["options"].size()).is_equal(2)

func test_present_thought_sets_ui_flag():
	var state = _initial_state.duplicate(true)
	var new_state = ThoughtSystemScript.present_thought(state, "test_thought")
	
	assert_that(new_state["meta"]["active_thought"]).is_equal("test_thought")

func test_thought_updates_convictions():
	var state = _initial_state.duplicate(true)
	state["meta"]["active_thought"] = "test_thought"
	
	# Choose option 0 (+2 violence)
	var new_state = ThoughtSystemScript.choose_thought(state, 0)
	
	assert_that(new_state["player"]["convictions"]["violence_thoughts"]).is_equal(2)
	assert_that(new_state["meta"]["active_thought"]).is_equal(null)

func test_negative_convictions_reduce_counters():
	var state = _initial_state.duplicate(true)
	state["player"]["convictions"]["violence_thoughts"] = 5
	state["meta"]["active_thought"] = "test_thought"
	
	# Choose option 1 (-1 violence)
	var new_state = ThoughtSystemScript.choose_thought(state, 1)
	
	assert_that(new_state["player"]["convictions"]["violence_thoughts"]).is_equal(4)

func test_multiple_thoughts_accumulate():
	var state = _initial_state.duplicate(true)
	state["meta"]["active_thought"] = "test_thought"
	
	# First choice (+2)
	state = ThoughtSystemScript.choose_thought(state, 0)
	
	# Present again (simulate chain)
	state = ThoughtSystemScript.present_thought(state, "test_thought")
	
	# Second choice (+2)
	state = ThoughtSystemScript.choose_thought(state, 0)
	
	assert_that(state["player"]["convictions"]["violence_thoughts"]).is_equal(4)
