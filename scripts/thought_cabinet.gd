extends Node
class_name ThoughtCabinet

## Thought Cabinet system inspired by Disco Elysium
## Players can internalize thoughts that provide bonuses/penalties

signal thought_added(thought: Thought)
signal thought_internalized(thought: Thought)
signal thought_removed(thought: Thought)
signal thought_cabinet_full
signal thought_not_found(thought_id: String)


class Thought:
	var id: String
	var title: String
	var description: String
	var is_internalized: bool = false
	var time_to_internalize: float = 0.0  # in seconds (for demo purposes)
	var effects: Dictionary = {}  # stat modifiers when internalized

	func _init(
		_id: String,
		_title: String,
		_description: String,
		_time: float = 0.0,
		_effects: Dictionary = {}
	):
		id = _id
		title = _title
		description = _description
		time_to_internalize = _time
		effects = _effects


var available_thoughts: Array[Thought] = []
var active_thoughts: Array[Thought] = []
var max_active_thoughts: int = 3


func _ready():
	# Initialize some example thoughts related to post-Gothic 2 world
	add_available_thought(
		Thought.new(
			"aftermath_trauma",
			"The Weight of Victory",
			"You saved the world, but at what cost? The faces of those who fell haunt you still.",
			5.0,
			{"empathy": 1, "morale": -5}
		)
	)

	add_available_thought(
		Thought.new(
			"dragon_slayer",
			"Slayer of Dragons",
			"You've faced dragons and lived. What could possibly frighten you now?",
			5.0,
			{"authority": 2, "pain_threshold": 1}
		)
	)

	add_available_thought(
		Thought.new(
			"khorinis_nostalgia",
			"Memories of Khorinis",
			"The island, the people, the struggles... it all seems so distant now.",
			3.0,
			{"perception": 1, "shivers": 1}
		)
	)

	add_available_thought(
		Thought.new(
			"beliar_influence",
			"Touched by Darkness",
			"The battle with evil left its mark. You sense things others cannot.",
			10.0,
			{"shivers": 2, "empathy": -1, "health": -10}
		)
	)


func add_available_thought(thought: Thought):
	"""Add a new thought that can be internalized"""
	if not has_thought(thought.id):
		available_thoughts.append(thought)
		thought_added.emit(thought)


func internalize_thought(thought_id: String) -> bool:
	"""Start internalizing a thought"""
	if active_thoughts.size() >= max_active_thoughts:
		thought_cabinet_full.emit()
		return false

	var thought = get_thought_by_id(thought_id)
	if thought and not thought.is_internalized:
		thought.is_internalized = true
		active_thoughts.append(thought)
		available_thoughts.erase(thought)
		thought_internalized.emit(thought)
		return true

	thought_not_found.emit(thought_id)
	return false


func remove_thought(thought_id: String) -> bool:
	"""Remove an internalized thought"""
	var thought = get_active_thought_by_id(thought_id)
	if thought:
		active_thoughts.erase(thought)
		thought.is_internalized = false
		available_thoughts.append(thought)
		thought_removed.emit(thought)
		return true
	return false


func get_thought_by_id(thought_id: String) -> Thought:
	"""Find a thought by its ID in available thoughts"""
	for thought in available_thoughts:
		if thought.id == thought_id:
			return thought
	return null


func get_active_thought_by_id(thought_id: String) -> Thought:
	"""Find an active thought by its ID"""
	for thought in active_thoughts:
		if thought.id == thought_id:
			return thought
	return null


func has_thought(thought_id: String) -> bool:
	"""Check if a thought exists (available or active)"""
	return get_thought_by_id(thought_id) != null or get_active_thought_by_id(thought_id) != null


func get_total_effects() -> Dictionary:
	"""Calculate total stat modifiers from all internalized thoughts"""
	var total_effects = {}
	for thought in active_thoughts:
		if thought.is_internalized:
			for stat in thought.effects:
				if stat in total_effects:
					total_effects[stat] += thought.effects[stat]
				else:
					total_effects[stat] = thought.effects[stat]
	return total_effects


func get_thoughts_summary() -> String:
	"""Get a formatted summary of all thoughts"""
	var summary = "=== THOUGHT CABINET ===\n"
	summary += "Active Thoughts (%d/%d):\n" % [active_thoughts.size(), max_active_thoughts]

	for thought in active_thoughts:
		summary += "  - %s: %s\n" % [thought.title, thought.description]

	if available_thoughts.size() > 0:
		summary += "\nAvailable Thoughts:\n"
		for thought in available_thoughts:
			summary += "  - %s: %s\n" % [thought.title, thought.description]

	return summary
