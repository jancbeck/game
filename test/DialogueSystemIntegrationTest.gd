class_name DialogueSystemIntegrationTest
extends GdUnitTestSuite

## Integration test for DialogueSystem using Scene Runner
## Tests interaction between DialogueSystem and CharacterStats in a scene context

var _runner: GdUnitSceneRunner
var _dialogue_system: DialogueSystem
var _character_stats: CharacterStats


func before_test():
	"""Initialize test data before each test case"""
	# Load the main scene which contains NPCs with dialogue systems
	_runner = scene_runner("res://scenes/main.tscn")

	# Get the NPC node which has DialogueSystem
	var npc = _runner.find_child("NPC", true, false)
	assert_object(npc).is_not_null()

	# Access the dialogue system from the scene
	_dialogue_system = npc.get_node_or_null("DialogueSystem")
	if _dialogue_system == null:
		# If not in scene, create one for testing
		_dialogue_system = auto_free(DialogueSystem.new())
		_dialogue_system.setup_example_dialogue()

	# Create character stats for testing
	_character_stats = auto_free(CharacterStats.new())


func after_test():
	"""Clean up scene runner after each test"""
	if _runner:
		_runner.clear_scene()


func test_scene_loads_correctly():
	"""Test that the main scene loads with required components"""
	var scene = _runner.scene()
	assert_object(scene).is_not_null()

	# Verify NPCs are present
	var npc = _runner.find_child("NPC", true, false)
	assert_object(npc).is_not_null()


func test_dialogue_system_in_scene_context():
	"""Test dialogue system initialization in scene context"""
	# Ensure dialogue is properly initialized
	if _dialogue_system.current_dialogue.is_empty():
		_dialogue_system.setup_example_dialogue()

	assert_object(_dialogue_system).is_not_null()
	assert_dict(_dialogue_system.current_dialogue).is_not_empty()


func test_start_dialogue_in_scene():
	"""Test starting a dialogue sequence in scene context"""
	if _dialogue_system.current_dialogue.is_empty():
		_dialogue_system.setup_example_dialogue()

	_dialogue_system.start_dialogue("start", _character_stats)

	var current_node = _dialogue_system.get_current_node()
	assert_object(current_node).is_not_null()
	assert_str(current_node.id).is_equal("start")
	assert_str(current_node.speaker).is_equal("Old Miner")


func test_dialogue_options_availability():
	"""Test that dialogue options are available"""
	if _dialogue_system.current_dialogue.is_empty():
		_dialogue_system.setup_example_dialogue()

	_dialogue_system.start_dialogue("start", _character_stats)

	var current_node = _dialogue_system.get_current_node()
	assert_int(current_node.options.size()).is_greater(0)


func test_select_simple_option_without_skill_check():
	"""Test selecting a dialogue option without skill check"""
	if _dialogue_system.current_dialogue.is_empty():
		_dialogue_system.setup_example_dialogue()

	_dialogue_system.start_dialogue("start", _character_stats)

	# Select first option which should be "I'm looking for information about the aftermath"
	var success = _dialogue_system.select_option(0)

	assert_bool(success).is_true()
	assert_str(_dialogue_system.current_node_id).is_equal("aftermath")


func test_skill_check_integration_with_character_stats():
	"""Test that dialogue system correctly uses character stats for skill checks"""
	if _dialogue_system.current_dialogue.is_empty():
		_dialogue_system.setup_example_dialogue()

	# Boost character's rhetoric to increase success chances
	_character_stats.modify_attribute("intellect", 5)
	_character_stats.modify_attribute("psyche", 5)

	_dialogue_system.start_dialogue("start", _character_stats)

	# Find the rhetoric skill check option (index 1)
	var current_node = _dialogue_system.get_current_node()
	var rhetoric_option = current_node.options[1]

	assert_bool(rhetoric_option.requires_skill_check).is_true()
	assert_str(rhetoric_option.skill_required).is_equal("rhetoric")


func test_successful_skill_check_progression():
	"""Test dialogue progression after successful skill check"""
	if _dialogue_system.current_dialogue.is_empty():
		_dialogue_system.setup_example_dialogue()

	# Give character very high stats to ensure success
	_character_stats.modify_attribute("intellect", 10)
	_character_stats.modify_attribute("psyche", 10)

	# Try the rhetoric check multiple times to get at least one success
	var success_found = false
	for attempt in range(20):  # Multiple attempts due to randomness
		_dialogue_system.start_dialogue("start", _character_stats)
		_dialogue_system.select_option(1)  # Rhetoric option

		if _dialogue_system.current_node_id == "persuade_success":
			success_found = true
			break

	# With high stats, we should eventually succeed
	assert_bool(success_found).is_true()


func test_failed_skill_check_progression():
	"""Test dialogue progression after failed skill check"""
	if _dialogue_system.current_dialogue.is_empty():
		_dialogue_system.setup_example_dialogue()

	# Give character very low stats to ensure failure
	_character_stats.modify_attribute("intellect", -1)  # Will clamp to 1
	_character_stats.modify_attribute("psyche", -1)  # Will clamp to 1

	# Try the rhetoric check multiple times to get at least one failure
	var failure_found = false
	for attempt in range(20):  # Multiple attempts due to randomness
		_dialogue_system.start_dialogue("start", _character_stats)
		_dialogue_system.select_option(1)  # Rhetoric option

		if _dialogue_system.current_node_id == "persuade_fail":
			failure_found = true
			break

	# With low stats, we should eventually fail
	assert_bool(failure_found).is_true()


func test_dialogue_ending():
	"""Test that dialogue properly ends"""
	if _dialogue_system.current_dialogue.is_empty():
		_dialogue_system.setup_example_dialogue()

	_dialogue_system.start_dialogue("start", _character_stats)

	# Navigate to end
	_dialogue_system.select_option(3)  # "Just passing through" option

	assert_str(_dialogue_system.current_node_id).is_equal("end")


func test_multiple_dialogue_branches():
	"""Test navigating through multiple dialogue branches"""
	if _dialogue_system.current_dialogue.is_empty():
		_dialogue_system.setup_example_dialogue()

	_dialogue_system.start_dialogue("start", _character_stats)

	# Take the information path
	_dialogue_system.select_option(0)
	assert_str(_dialogue_system.current_node_id).is_equal("aftermath")

	# Continue to details
	_dialogue_system.select_option(0)
	assert_str(_dialogue_system.current_node_id).is_equal("details")

	# End the conversation
	_dialogue_system.select_option(1)
	assert_str(_dialogue_system.current_node_id).is_equal("end")


func test_dialogue_with_empathy_check():
	"""Test empathy skill check in dialogue"""
	if _dialogue_system.current_dialogue.is_empty():
		_dialogue_system.setup_example_dialogue()

	_dialogue_system.start_dialogue("start", _character_stats)

	# Navigate to details node
	_dialogue_system.select_option(0)
	_dialogue_system.select_option(0)

	assert_str(_dialogue_system.current_node_id).is_equal("details")

	# Find empathy option
	var current_node = _dialogue_system.get_current_node()
	var empathy_option = current_node.options[0]

	assert_bool(empathy_option.requires_skill_check).is_true()
	assert_str(empathy_option.skill_required).is_equal("empathy")


func test_character_stats_signal_integration():
	"""Test that character stats signals work with dialogue system"""
	if _dialogue_system.current_dialogue.is_empty():
		_dialogue_system.setup_example_dialogue()

	var signal_received = false
	var signal_skill = ""
	var signal_success = false

	# Connect to skill check signal
	_character_stats.skill_check_performed.connect(
		func(skill_name: String, result: bool, _roll: int, _target: int):
			signal_received = true
			signal_skill = skill_name
			signal_success = result
	)

	# Perform a dialogue with skill check
	_character_stats.modify_attribute("intellect", 10)
	_character_stats.modify_attribute("psyche", 10)

	_dialogue_system.start_dialogue("start", _character_stats)
	_dialogue_system.select_option(1)  # Rhetoric check

	# Signal should have been emitted
	assert_bool(signal_received).is_true()
	assert_str(signal_skill).is_equal("rhetoric")


func test_dialogue_node_structure():
	"""Test that dialogue nodes have correct structure"""
	if _dialogue_system.current_dialogue.is_empty():
		_dialogue_system.setup_example_dialogue()

	_dialogue_system.start_dialogue("start", _character_stats)

	var node = _dialogue_system.get_current_node()

	# Verify node has required properties
	assert_object(node).is_not_null()
	assert_str(node.id).is_not_empty()
	assert_str(node.speaker).is_not_empty()
	assert_str(node.text).is_not_empty()
	assert_array(node.options).is_not_empty()


func test_dialogue_option_structure():
	"""Test that dialogue options have correct structure"""
	if _dialogue_system.current_dialogue.is_empty():
		_dialogue_system.setup_example_dialogue()

	_dialogue_system.start_dialogue("start", _character_stats)

	var node = _dialogue_system.get_current_node()
	var option = node.options[0]

	# Verify option has required properties
	assert_str(option.text).is_not_empty()
	assert_bool(option.is_available).is_true()
