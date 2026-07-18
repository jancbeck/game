class_name Reducers
extends RefCounted
## Pure static reducers. Each takes a state Dictionary (already a private
## copy handed over by Store.dispatch) plus arguments, and returns the next
## state. No engine access, no side effects — fully unit-testable headless.

const HARDENED_THRESHOLD := 0


static func start_quest(state: Dictionary, quest_id: String) -> Dictionary:
	var quests: Dictionary = state["quests"]
	if quest_id in quests["active"] or quests["completed"].has(quest_id):
		return state
	quests["active"].append(quest_id)
	return state


static func complete_quest(state: Dictionary, quest_id: String, approach: String) -> Dictionary:
	var quests: Dictionary = state["quests"]
	if quests["completed"].has(quest_id):
		return state
	quests["active"].erase(quest_id)
	quests["completed"][quest_id] = approach
	return state


static func set_flag(state: Dictionary, flag: String) -> Dictionary:
	if flag in state["flags"]:
		return state
	state["flags"].append(flag)
	return state


static func add_journal_entry(state: Dictionary, text: String) -> Dictionary:
	state["journal"].append(text)
	return state


## The specialization mechanic: using an approach raises the attribute you
## leaned on and hardens you — every OTHER attribute loses flexibility.
## An attribute whose flexibility reaches 0 is "hardened": dialogue options
## that need it to grow further are locked forever.
static func apply_approach(state: Dictionary, attr_id: String, cost: int = 2) -> Dictionary:
	var attributes: Dictionary = state["player"]["attributes"]
	if not attributes.has(attr_id):
		push_error("Unknown attribute: %s" % attr_id)
		return state
	attributes[attr_id]["score"] += 1
	for other_id: String in attributes:
		if other_id == attr_id:
			continue
		var flex: int = attributes[other_id]["flexibility"]
		attributes[other_id]["flexibility"] = maxi(HARDENED_THRESHOLD, flex - cost)
	return state


## Apply a dialogue option's declared effects (data-driven).
static func apply_effects(state: Dictionary, effects: Array) -> Dictionary:
	for effect: Dictionary in effects:
		match effect.get("type", ""):
			"start_quest":
				state = start_quest(state, effect["quest"])
			"complete_quest":
				state = complete_quest(state, effect["quest"], effect.get("approach", ""))
			"set_flag":
				state = set_flag(state, effect["flag"])
			"apply_approach":
				state = apply_approach(state, effect["attribute"], int(effect.get("cost", 2)))
			"journal":
				state = add_journal_entry(state, effect["text"])
			_:
				push_error("Unknown effect type: %s" % str(effect))
	return state


# --- Pure queries (selectors) ---


static func is_hardened(state: Dictionary, attr_id: String) -> bool:
	var attributes: Dictionary = state["player"]["attributes"]
	return attributes.has(attr_id) and attributes[attr_id]["flexibility"] <= HARDENED_THRESHOLD


static func attribute_score(state: Dictionary, attr_id: String) -> int:
	var attributes: Dictionary = state["player"]["attributes"]
	return int(attributes[attr_id]["score"]) if attributes.has(attr_id) else 0


static func has_flag(state: Dictionary, flag: String) -> bool:
	return flag in state["flags"]


static func quest_completed(state: Dictionary, quest_id: String) -> bool:
	return state["quests"]["completed"].has(quest_id)


static func quest_active(state: Dictionary, quest_id: String) -> bool:
	return quest_id in state["quests"]["active"]


## Journal entries in reverse-chronological order (newest first), for the
## narrative HUD's journal panel. Returns a fresh copy; never the live array.
static func journal_log(state: Dictionary) -> Array:
	var entries: Array = state["journal"].duplicate()
	entries.reverse()
	return entries


## Quest log rows for the narrative HUD: active quests first (in the order
## they were started), then completed ones with the approach taken. Titles
## are resolved from Db by the panel; this stays engine-free and testable.
static func quest_log(state: Dictionary) -> Array:
	var rows: Array = []
	for quest_id: String in state["quests"]["active"]:
		rows.append({"id": quest_id, "done": false, "approach": ""})
	var completed: Dictionary = state["quests"]["completed"]
	for quest_id: String in completed:
		rows.append({"id": quest_id, "done": true, "approach": str(completed[quest_id])})
	return rows


## Evaluate a dialogue option's "requires" block against state.
## Supported keys:
##   attributes: {attr_id: min_score}
##   not_hardened: [attr_id, ...]  — attr must still be flexible to grow
##   flags / not_flags: [flag, ...]
##   quest_active / quest_completed / quest_not_completed: [quest_id, ...]
static func requirements_met(state: Dictionary, requires: Dictionary) -> bool:
	var min_scores: Dictionary = requires.get("attributes", {})
	for attr_id: String in min_scores:
		if attribute_score(state, attr_id) < int(min_scores[attr_id]):
			return false
	for attr_id: String in requires.get("not_hardened", []):
		if is_hardened(state, attr_id):
			return false
	for flag: String in requires.get("flags", []):
		if not has_flag(state, flag):
			return false
	for flag: String in requires.get("not_flags", []):
		if has_flag(state, flag):
			return false
	for quest_id: String in requires.get("quest_active", []):
		if not quest_active(state, quest_id):
			return false
	for quest_id: String in requires.get("quest_completed", []):
		if not quest_completed(state, quest_id):
			return false
	for quest_id: String in requires.get("quest_not_completed", []):
		if quest_completed(state, quest_id):
			return false
	return true
