# scripts/core/quest_system.gd
class_name QuestSystem
extends RefCounted


## Starts a quest, marking its status as 'active'.
## Returns new state with quest marked active.
##
## Example:
##   var new_state = QuestSystem.start_quest(state, "rescue_prisoner")
static func start_quest(state: Dictionary, quest_id: String) -> Dictionary:
	var new_state = state.duplicate(true)

	if not new_state["quests"].has(quest_id):
		push_error("Quest not found in state: " + quest_id)
		return state

	if new_state["quests"][quest_id]["status"] != "available":
		push_error("Quest is not available to start: " + quest_id)
		return state

	new_state["quests"][quest_id]["status"] = "active"
	return new_state


## Completes a quest using specified approach.
## Returns new state with quest marked complete, stats degraded,
## and consequences applied.
##
## Example:
##   var new_state = QuestSystem.complete_quest(
##     state,
##     "rescue_prisoner",
##     "violent"
##   )
static func complete_quest(state: Dictionary, quest_id: String, approach: String) -> Dictionary:
	var new_state = state.duplicate(true)

	# Validate quest exists and is active
	if not new_state["quests"].has(quest_id):
		push_error("Quest not found: " + quest_id)
		return state

	if new_state["quests"][quest_id]["status"] != "active":
		push_error("Quest not active: " + quest_id)
		return state

	# Load quest data
	var quest_data = DataLoader.get_quest(quest_id)
	if not quest_data.has("approaches") or not quest_data["approaches"].has(approach):
		push_error("Approach '%s' not found for quest '%s'." % [approach, quest_id])
		return state

	var approach_data = quest_data["approaches"][approach]

	# Apply degradation
	if approach_data.has("degrades"):
		for stat in approach_data["degrades"]:
			var stat_name = stat.replace("flexibility_", "")
			var amount = approach_data["degrades"][stat]
			new_state = PlayerSystem.modify_flexibility(new_state, stat_name, amount)

	# Apply conviction rewards
	if approach_data.has("rewards") and approach_data["rewards"].has("convictions"):
		for conviction in approach_data["rewards"]["convictions"]:
			var amount = approach_data["rewards"]["convictions"][conviction]
			new_state = PlayerSystem.modify_conviction(new_state, conviction, amount)

	# Set memory flags
	if approach_data.has("rewards") and approach_data["rewards"].has("memory_flags"):
		for flag in approach_data["rewards"]["memory_flags"]:
			# Assuming flags are in format "npc_id_flag_name"
			# We use rsplit to allow npc_id to contain underscores.
			# The LAST part is the flag name.
			var parts = flag.rsplit("_", true, 1)
			if parts.size() == 2:
				var npc_id = parts[0]
				var flag_name = parts[1]

				if new_state["world"]["npc_states"].has(npc_id):
					if not new_state["world"]["npc_states"][npc_id]["memory_flags"].has(flag_name):
						new_state["world"]["npc_states"][npc_id]["memory_flags"].append(flag_name)
				else:
					push_warning("Attempted to set memory flag for non-existent NPC: " + npc_id)
			else:
				push_warning(
					"Memory flag format incorrect: " + flag + ". Expected 'npc_id_flag_name'."
				)

	# Mark quest complete
	new_state["quests"][quest_id]["status"] = "completed"
	new_state["quests"][quest_id]["approach_taken"] = approach

	# Unlock follow-up quests
	if quest_data.has("outcomes") and quest_data["outcomes"].has("all"):
		for outcome in quest_data["outcomes"]["all"]:
			if outcome.has("advance_to"):
				var next_quest_id = outcome["advance_to"]
				# Check if the quest data exists for the next quest before adding
				if (
					not new_state["quests"].has(next_quest_id)
					and not DataLoader.get_quest(next_quest_id).is_empty()
				):
					new_state["quests"][next_quest_id] = {
						"status": "available", "approach_taken": "", "objectives_completed": []
					}
				elif new_state["quests"].has(next_quest_id):
					push_warning(
						"Attempted to unlock quest '%s' that is already in state." % next_quest_id
					)
				else:
					push_warning(
						"Attempted to unlock quest '%s' but no quest data found." % next_quest_id
					)

			if outcome.has("unlock_location"):
				var location_id = outcome["unlock_location"]
				new_state["world"]["location_flags"][location_id] = true

	return new_state
