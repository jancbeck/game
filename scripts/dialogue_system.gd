class_name DialogueSystem
extends Node

## Dialogue system with skill checks inspired by Disco Elysium

signal dialogue_started(npc_name: String)
signal dialogue_option_selected(option: DialogueOption)
signal dialogue_ended
signal skill_check_result(success: bool, skill: String)


class DialogueOption:
	var text: String
	var next_node_id: String
	var requires_skill_check: bool = false
	var skill_required: String = ""
	var skill_difficulty: int = 0
	var is_available: bool = true

	func _init(_text: String, _next: String = "", _skill: String = "", _difficulty: int = 0):
		text = _text
		next_node_id = _next
		if _skill != "":
			requires_skill_check = true
			skill_required = _skill
			skill_difficulty = _difficulty


class DialogueNode:
	var id: String
	var speaker: String
	var text: String
	var options: Array[DialogueOption] = []

	func _init(_id: String, _speaker: String, _text: String):
		id = _id
		speaker = _speaker
		text = _text

	func add_option(option: DialogueOption):
		options.append(option)


var current_dialogue: Dictionary = {}
var current_node_id: String = ""
var character_stats: CharacterStats = null


func _ready():
	# Example dialogue for testing
	setup_example_dialogue()


func setup_example_dialogue():
	"""Create example dialogue tree for post-Gothic 2 world"""
	var dialogue = {}

	var start = DialogueNode.new(
		"start",
		"Old Miner",
		"Well, well... if it isn't the hero who saved us all. What brings you to these parts?"
	)
	start.add_option(
		DialogueOption.new("I'm looking for information about the aftermath.", "aftermath")
	)
	start.add_option(
		DialogueOption.new("[Rhetoric] Convince him you need his help.", "persuade", "rhetoric", 8)
	)
	start.add_option(
		DialogueOption.new(
			"[Perception] Notice something off about him.", "perceive", "perception", 7
		)
	)
	start.add_option(DialogueOption.new("Just passing through.", "end"))
	dialogue["start"] = start

	var aftermath = (
		DialogueNode
		. new(
			"aftermath",
			"Old Miner",
			"The mines are quiet now. Too quiet. The orcs are gone, but something else stirs in the deep."
		)
	)
	aftermath.add_option(DialogueOption.new("Tell me more about what you've seen.", "details"))
	aftermath.add_option(DialogueOption.new("I should investigate.", "end"))
	dialogue["aftermath"] = aftermath

	var details = (
		DialogueNode
		. new(
			"details",
			"Old Miner",
			(
				"Strange lights, whispers in the dark. "
				+ "Some say it's Beliar's curse, others say it's just fear. "
				+ "But I know what I saw..."
			)
		)
	)
	details.add_option(
		DialogueOption.new("[Empathy] Comfort him about his fears.", "comfort", "empathy", 6)
	)
	details.add_option(DialogueOption.new("I'll look into it.", "end"))
	dialogue["details"] = details

	var comfort = DialogueNode.new(
		"comfort",
		"Old Miner",
		"Thank you... it's been hard. Not many understand what we went through."
	)
	comfort.add_option(DialogueOption.new("We all carry scars from that time.", "end"))
	dialogue["comfort"] = comfort

	var persuade_success = DialogueNode.new(
		"persuade_success",
		"Old Miner",
		"Alright, alright. I can see you mean business. I'll tell you what I know..."
	)
	persuade_success.add_option(DialogueOption.new("Go on.", "details"))
	dialogue["persuade_success"] = persuade_success

	var persuade_fail = DialogueNode.new(
		"persuade_fail",
		"Old Miner",
		"Nice try, but I'm not that easy to sway. Come back when you've got more to offer."
	)
	persuade_fail.add_option(DialogueOption.new("Fine.", "end"))
	dialogue["persuade_fail"] = persuade_fail

	var perceive_success = (
		DialogueNode
		. new(
			"perceive_success",
			"Old Miner",
			"[You notice his hands trembling, and dried blood under his fingernails. He's hiding something.]"
		)
	)
	perceive_success.add_option(
		DialogueOption.new(
			"[Authority] Tell me what you're hiding. Now.", "details", "authority", 8
		)
	)
	perceive_success.add_option(DialogueOption.new("Let it go.", "end"))
	dialogue["perceive_success"] = perceive_success

	var perceive_fail = DialogueNode.new(
		"perceive_fail", "Old Miner", "[He seems like a typical old miner. Nothing unusual.]"
	)
	perceive_fail.add_option(DialogueOption.new("Tell me about the aftermath.", "aftermath"))
	perceive_fail.add_option(DialogueOption.new("I'll be going.", "end"))
	dialogue["perceive_fail"] = perceive_fail

	var end = DialogueNode.new("end", "Old Miner", "Safe travels, hero.")
	dialogue["end"] = end

	current_dialogue = dialogue


func start_dialogue(start_node: String = "start", stats: CharacterStats = null):
	"""Begin a dialogue sequence"""
	character_stats = stats
	current_node_id = start_node
	if current_node_id in current_dialogue:
		dialogue_started.emit(current_dialogue[current_node_id].speaker)


func get_current_node() -> DialogueNode:
	"""Get the current dialogue node"""
	if current_node_id in current_dialogue:
		return current_dialogue[current_node_id]
	return null


func select_option(option_index: int) -> bool:
	"""Select a dialogue option and handle skill checks"""
	var node = get_current_node()
	if node and option_index < node.options.size():
		var option = node.options[option_index]
		dialogue_option_selected.emit(option)

		if option.requires_skill_check and character_stats:
			var check_result = character_stats.perform_skill_check(
				option.skill_required, option.skill_difficulty
			)

			skill_check_result.emit(check_result.success, option.skill_required)

			# Handle success/failure paths
			if check_result.success:
				if option.next_node_id + "_success" in current_dialogue:
					current_node_id = option.next_node_id + "_success"
				else:
					current_node_id = option.next_node_id
			else:
				if option.next_node_id + "_fail" in current_dialogue:
					current_node_id = option.next_node_id + "_fail"
				else:
					current_node_id = option.next_node_id
		else:
			current_node_id = option.next_node_id

		if current_node_id == "end" or current_node_id == "":
			dialogue_ended.emit()
			return false

		return true
	return false
