class_name SaveSystem
extends RefCounted

## Handles serialization and deserialization of the game state.
## Stores data in user://save.dat (Variant format).

const SAVE_PATH = "user://save.dat"


## Saves the current state to disk.
static func save_state(state: Dictionary) -> void:
	var file = FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file:
		# Use var_to_str to handle Godot types like Vector3 correctly
		file.store_string(var_to_str(state))
		print("Game saved to " + SAVE_PATH)
	else:
		push_error("Failed to save game to " + SAVE_PATH)


## Loads the state from disk. returns empty Dictionary if failed.
static func load_state() -> Dictionary:
	if not FileAccess.file_exists(SAVE_PATH):
		push_warning("No save file found at " + SAVE_PATH)
		return {}

	var file = FileAccess.open(SAVE_PATH, FileAccess.READ)
	if not file:
		push_error("Failed to open save file " + SAVE_PATH)
		return {}

	var content = file.get_as_text()
	# Use str_to_var to restore Godot types
	var data = str_to_var(content)

	if typeof(data) != TYPE_DICTIONARY:
		push_error("Save file corrupted or invalid format")
		return {}

	print("Game loaded from " + SAVE_PATH)
	return data
