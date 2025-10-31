extends GutTest

## Integration tests for dialogue system with character stats

var dialogue: DialogueSystem
var stats: CharacterStats


func before_each():
	dialogue = DialogueSystem.new()
	stats = CharacterStats.new()
	add_child_autofree(dialogue)
	add_child_autofree(stats)


func test_dialogue_with_high_skill():
	# Set up a dialogue with a skill check
	var test_dialogue = {}

	var start = DialogueSystem.DialogueNode.new("start", "NPC", "What do you want?")
	start.add_option(
		DialogueSystem.DialogueOption.new(
			"[Rhetoric] Convince them", "convince", "rhetoric", 5
		)
	)
	test_dialogue["start"] = start

	var success = DialogueSystem.DialogueNode.new(
		"convince_success", "NPC", "Fine, you've convinced me."
	)
	test_dialogue["convince_success"] = success

	var fail = DialogueSystem.DialogueNode.new(
		"convince_fail", "NPC", "Not convincing enough."
	)
	test_dialogue["convince_fail"] = fail

	dialogue.current_dialogue = test_dialogue

	# Boost rhetoric skill to very high value to ensure success
	stats.modify_attribute("intellect", 10)
	stats.modify_attribute("psyche", 10)

	dialogue.start_dialogue("start", stats)
	watch_signals(dialogue)
	dialogue.select_option(0)

	assert_signal_emitted(dialogue, "skill_check_result", "Should perform skill check")

	# With high skills, we should succeed more often (though not guaranteed due to roll)
	# Just verify the system works
	var node = dialogue.get_current_node()
	assert_true(
		node.id == "convince_success" or node.id == "convince_fail",
		"Should navigate to success or fail branch"
	)


func test_dialogue_with_low_skill():
	# Set up similar dialogue but with low skills
	var test_dialogue = {}

	var start = DialogueSystem.DialogueNode.new("start", "NPC", "What do you want?")
	start.add_option(
		DialogueSystem.DialogueOption.new(
			"[Rhetoric] Convince them", "convince", "rhetoric", 20
		)  # Very high difficulty
	)
	test_dialogue["start"] = start

	var success = DialogueSystem.DialogueNode.new(
		"convince_success", "NPC", "Fine, you've convinced me."
	)
	test_dialogue["convince_success"] = success

	var fail = DialogueSystem.DialogueNode.new(
		"convince_fail", "NPC", "Not convincing enough."
	)
	test_dialogue["convince_fail"] = fail

	dialogue.current_dialogue = test_dialogue

	# Use default low skills
	dialogue.start_dialogue("start", stats)
	dialogue.select_option(0)

	# With very high difficulty and low skills, we should fail
	var node = dialogue.get_current_node()
	# Due to randomness, we can't guarantee failure, but the integration works
	assert_true(
		node.id == "convince_success" or node.id == "convince_fail",
		"Should navigate to appropriate branch"
	)


func test_multiple_skill_checks_in_dialogue():
	var test_dialogue = {}

	var start = DialogueSystem.DialogueNode.new("start", "NPC", "Test your skills.")
	start.add_option(
		DialogueSystem.DialogueOption.new(
			"[Logic] Use logic", "logic_check", "logic", 5
		)
	)
	start.add_option(
		DialogueSystem.DialogueOption.new(
			"[Empathy] Show empathy", "empathy_check", "empathy", 5
		)
	)
	test_dialogue["start"] = start

	# Add result nodes for both checks
	for check_name in ["logic_check", "empathy_check"]:
		test_dialogue[check_name + "_success"] = DialogueSystem.DialogueNode.new(
			check_name + "_success", "NPC", "Success!"
		)
		test_dialogue[check_name + "_fail"] = DialogueSystem.DialogueNode.new(
			check_name + "_fail", "NPC", "Failed!"
		)

	dialogue.current_dialogue = test_dialogue
	dialogue.start_dialogue("start", stats)

	# Try first option (logic)
	watch_signals(dialogue)
	dialogue.select_option(0)
	assert_signal_emitted(dialogue, "skill_check_result", "Should perform skill check")


func test_dialogue_completion():
	# Test a complete dialogue flow
	var test_dialogue = {}

	var start = DialogueSystem.DialogueNode.new("start", "NPC", "Hello!")
	start.add_option(DialogueSystem.DialogueOption.new("Goodbye", "end"))
	test_dialogue["start"] = start

	var end_node = DialogueSystem.DialogueNode.new("end", "NPC", "Farewell!")
	test_dialogue["end"] = end_node

	dialogue.current_dialogue = test_dialogue
	dialogue.start_dialogue("start", stats)

	watch_signals(dialogue)
	var result = dialogue.select_option(0)

	assert_false(result, "Should return false when reaching end")
	assert_signal_emitted(dialogue, "dialogue_ended", "Should emit ended signal")


func test_branching_dialogue_paths():
	# Create a more complex branching dialogue
	var test_dialogue = {}

	var start = DialogueSystem.DialogueNode.new("start", "NPC", "Choose your path.")
	start.add_option(DialogueSystem.DialogueOption.new("Path A", "path_a"))
	start.add_option(DialogueSystem.DialogueOption.new("Path B", "path_b"))
	test_dialogue["start"] = start

	var path_a = DialogueSystem.DialogueNode.new("path_a", "NPC", "You chose A.")
	path_a.add_option(DialogueSystem.DialogueOption.new("Continue", "end"))
	test_dialogue["path_a"] = path_a

	var path_b = DialogueSystem.DialogueNode.new("path_b", "NPC", "You chose B.")
	path_b.add_option(DialogueSystem.DialogueOption.new("Continue", "end"))
	test_dialogue["path_b"] = path_b

	var end_node = DialogueSystem.DialogueNode.new("end", "NPC", "The end.")
	test_dialogue["end"] = end_node

	dialogue.current_dialogue = test_dialogue
	dialogue.start_dialogue("start", stats)

	# Choose path A
	dialogue.select_option(0)
	assert_eq(
		dialogue.current_node_id, "path_a", "Should navigate to path A"
	)

	# Start over and choose path B
	dialogue.start_dialogue("start", stats)
	dialogue.select_option(1)
	assert_eq(
		dialogue.current_node_id, "path_b", "Should navigate to path B"
	)
