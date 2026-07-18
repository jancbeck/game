extends Node
## Read-only content database. Loads all JSON under res://data/ at startup.
## Content errors are fatal in debug: fail loudly, never silently skip.

var dialogues: Dictionary = {}
var quests: Dictionary = {}
var scenes: Dictionary = {}
var chapters: Dictionary = {}


func _ready() -> void:
	load_all()


func load_all() -> void:
	dialogues = _load_dir("res://data/dialogues")
	quests = _load_dir("res://data/quests")
	scenes = _load_dir("res://data/scenes")
	chapters = _load_chapters("res://data/chapters.json")


## The ordered act state machine (a single file, not a directory, because
## acts are ordered and a dict keyed by id would lose that order).
func get_chapters() -> Dictionary:
	return chapters


static func _load_chapters(path: String) -> Dictionary:
	var parsed: Variant = _load_json(path)
	if parsed is Dictionary and parsed.has("acts"):
		return parsed
	push_error("Invalid chapters file (needs an 'acts' array): %s" % path)
	return {}


func get_scene(id: String) -> Dictionary:
	if not scenes.has(id):
		push_error("Unknown scene: %s" % id)
		return {}
	return scenes[id]


func get_dialogue(id: String) -> Dictionary:
	if not dialogues.has(id):
		push_error("Unknown dialogue: %s" % id)
		return {}
	return dialogues[id]


func get_quest(id: String) -> Dictionary:
	if not quests.has(id):
		push_error("Unknown quest: %s" % id)
		return {}
	return quests[id]


static func _load_dir(dir_path: String) -> Dictionary:
	var result := {}
	var dir := DirAccess.open(dir_path)
	if dir == null:
		push_error("Missing content directory: %s" % dir_path)
		return result
	for file_name in dir.get_files():
		if not file_name.ends_with(".json"):
			continue
		var path := dir_path.path_join(file_name)
		var parsed: Variant = _load_json(path)
		if parsed is Dictionary and parsed.has("id"):
			result[parsed["id"]] = parsed
		else:
			push_error("Invalid content file (needs an 'id' field): %s" % path)
	return result


static func _load_json(path: String) -> Variant:
	var text := FileAccess.get_file_as_string(path)
	if text.is_empty():
		push_error("Cannot read: %s" % path)
		return null
	var json := JSON.new()
	if json.parse(text) != OK:
		push_error(
			"JSON error in %s line %d: %s" % [path, json.get_error_line(), json.get_error_message()]
		)
		return null
	return json.data
