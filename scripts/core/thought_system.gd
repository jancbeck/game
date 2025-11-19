class_name ThoughtSystem
extends RefCounted

## Manages the "internal monologue" system where players choose thoughts
## that accumulate convictions (violence, deceptive, compassionate).

## Presents a thought dialog to the player.
## Returns new state with the UI flag set to show the specific thought.
static func present_thought(state: Dictionary, thought_id: String) -> Dictionary:
	var new_state = state.duplicate(true)
	
	# Validate thought exists
	var thought_data = DataLoader.get_thought(thought_id)
	if thought_data.is_empty():
		push_error("Cannot present non-existent thought: " + thought_id)
		return state
		
	if not new_state.has("meta"):
		new_state["meta"] = {}
		
	new_state["meta"]["active_thought"] = thought_id
	return new_state

## Processes the player's choice for the active thought.
## Applies conviction changes and clears the active thought flag.
## option_index is 0-based index into the thought's "options" array.
static func choose_thought(state: Dictionary, option_index: int) -> Dictionary:
	var new_state = state.duplicate(true)
	
	if not new_state.has("meta") or not new_state["meta"].has("active_thought"):
		push_error("No active thought to choose from.")
		return state
		
	var thought_id = new_state["meta"]["active_thought"]
	var thought_data = DataLoader.get_thought(thought_id)
	
	if thought_data.is_empty():
		# Should not happen if present_thought validated it, but safety first
		new_state["meta"].erase("active_thought") 
		return new_state
		
	if option_index < 0 or option_index >= thought_data["options"].size():
		push_error("Invalid option index %d for thought %s" % [option_index, thought_id])
		return state
		
	var option = thought_data["options"][option_index]
	
	# Apply convictions
	if option.has("convictions"):
		for conviction in option["convictions"]:
			var amount = option["convictions"][conviction]
			new_state = PlayerSystem.modify_conviction(new_state, conviction, amount)
			
	# Clear active thought
	new_state["meta"]["active_thought"] = null
	
	return new_state

## Helper to find a thought ID that matches a specific trigger string.
## Returns empty string if no match found.
## In a larger game, we might cache this map.
static func get_thought_for_trigger(trigger_string: String) -> String:
	# This is inefficient for a large DB, but fine for prototype.
	# We need to scan files. Ideally DataLoader would provide a list of IDs.
	# For now, let's hardcode the known ones or implement a scanner in DataLoader.
	# Or, let's just rely on known IDs since we are making example files.
	
	# A better way for this phase: 
	# We know the files we created: after_violent_quest, after_diplomatic_quest
	var known_thoughts = ["after_violent_quest", "after_diplomatic_quest"]
	
	for id in known_thoughts:
		var data = DataLoader.get_thought(id)
		if data.has("trigger") and data["trigger"] == trigger_string:
			return id
			
	return ""
