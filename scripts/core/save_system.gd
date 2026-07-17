class_name SaveSystem
extends RefCounted
## Save/load: the store state IS the save file. Nothing else is persisted.

const SAVE_PATH := "user://save.json"


static func save_game(state: Dictionary, path: String = SAVE_PATH) -> bool:
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		push_error("Cannot open save file for writing: %s" % path)
		return false
	file.store_string(JSON.stringify(state, "\t"))
	file.close()
	return true


static func load_game(path: String = SAVE_PATH) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var text := FileAccess.get_file_as_string(path)
	var parsed: Variant = JSON.parse_string(text)
	if not parsed is Dictionary:
		push_error("Corrupt save file: %s" % path)
		return {}
	return _normalize(parsed)


## JSON round-trips lose int-ness (everything becomes float); fix the
## fields game logic compares as ints so ==/>= behave predictably.
static func _normalize(state: Dictionary) -> Dictionary:
	var attributes: Dictionary = state.get("player", {}).get("attributes", {})
	for attr_id: String in attributes:
		attributes[attr_id]["score"] = int(attributes[attr_id]["score"])
		attributes[attr_id]["flexibility"] = int(attributes[attr_id]["flexibility"])
	if state.has("version"):
		state["version"] = int(state["version"])
	return state
