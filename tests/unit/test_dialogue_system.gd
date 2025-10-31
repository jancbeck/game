extends GutTest

## Unit tests for DialogueSystem

var dialogue: DialogueSystem
var stats: CharacterStats


func before_each():
	dialogue = DialogueSystem.new()
	stats = CharacterStats.new()
	add_child_autofree(dialogue)
	add_child_autofree(stats)


func test_dialogue_node_creation():
	var node = DialogueSystem.DialogueNode.new("test_id", "Test NPC", "Hello there!")
	assert_eq(node.id, "test_id", "Node should have correct id")
	assert_eq(node.speaker, "Test NPC", "Node should have correct speaker")
	assert_eq(node.text, "Hello there!", "Node should have correct text")
	assert_eq(node.options.size(), 0, "Node should start with no options")


func test_dialogue_option_creation():
	var option = DialogueSystem.DialogueOption.new("Test option", "next_node")
	assert_eq(option.text, "Test option", "Option should have correct text")
	assert_eq(option.next_node_id, "next_node", "Option should have correct next node")
	assert_false(
		option.requires_skill_check, "Option without skill should not require check"
	)


func test_dialogue_option_with_skill_check():
	var option = DialogueSystem.DialogueOption.new(
		"[Rhetoric] Persuade them", "persuade", "rhetoric", 8
	)
	assert_true(
		option.requires_skill_check, "Option with skill should require check"
	)
	assert_eq(option.skill_required, "rhetoric", "Should have correct skill")
	assert_eq(option.skill_difficulty, 8, "Should have correct difficulty")


func test_add_option_to_node():
	var node = DialogueSystem.DialogueNode.new("test", "NPC", "Text")
	var option = DialogueSystem.DialogueOption.new("Reply", "next")
	node.add_option(option)
	assert_eq(node.options.size(), 1, "Should have one option")
	assert_eq(node.options[0], option, "Should have the correct option")


func test_start_dialogue():
	watch_signals(dialogue)
	dialogue.start_dialogue("start", stats)
	assert_signal_emitted(dialogue, "dialogue_started", "Should emit dialogue started signal")
	assert_eq(dialogue.current_node_id, "start", "Should set current node to start")
	assert_eq(dialogue.character_stats, stats, "Should store character stats reference")


func test_get_current_node():
	dialogue.start_dialogue("start", stats)
	var node = dialogue.get_current_node()
	assert_not_null(node, "Should return a node")
	assert_eq(node.id, "start", "Should return the start node")


func test_select_option_without_skill_check():
	dialogue.start_dialogue("start", stats)
	var initial_node = dialogue.get_current_node()

	# Select first option (should not require skill check based on example dialogue)
	var success = dialogue.select_option(0)

	# If it's not an end node, should return true
	if dialogue.current_node_id != "end":
		assert_true(success, "Should successfully select option")
	else:
		assert_false(success, "Should return false for end node")


func test_select_option_emits_signal():
	watch_signals(dialogue)
	dialogue.start_dialogue("start", stats)
	dialogue.select_option(0)
	assert_signal_emitted(
		dialogue, "dialogue_option_selected", "Should emit option selected signal"
	)


func test_dialogue_ends():
	dialogue.start_dialogue("start", stats)

	# Navigate to end node
	# This test assumes the example dialogue structure
	var current_node = dialogue.get_current_node()
	for i in range(current_node.options.size()):
		var option = current_node.options[i]
		if option.next_node_id == "end":
			watch_signals(dialogue)
			var result = dialogue.select_option(i)
			assert_false(result, "Should return false when dialogue ends")
			assert_signal_emitted(dialogue, "dialogue_ended", "Should emit dialogue ended signal")
			break


func test_skill_check_success_path():
	# Create a simple dialogue with skill check
	var test_dialogue = {}
	var start = DialogueSystem.DialogueNode.new("start", "Test", "Hello")
	start.add_option(
		DialogueSystem.DialogueOption.new("[Test] Check", "check", "logic", 2)
	)
	test_dialogue["start"] = start

	var success_node = DialogueSystem.DialogueNode.new(
		"check_success", "Test", "Success!"
	)
	test_dialogue["check_success"] = success_node

	var fail_node = DialogueSystem.DialogueNode.new("check_fail", "Test", "Failed!")
	test_dialogue["check_fail"] = fail_node

	dialogue.current_dialogue = test_dialogue
	dialogue.start_dialogue("start", stats)

	watch_signals(dialogue)
	dialogue.select_option(0)

	assert_signal_emitted(
		dialogue, "skill_check_result", "Should emit skill check result signal"
	)
	# The result depends on the roll, so we just check the signal was emitted


func test_invalid_option_index():
	dialogue.start_dialogue("start", stats)
	var result = dialogue.select_option(999)
	assert_false(result, "Should return false for invalid option index")
