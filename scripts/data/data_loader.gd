class_name DataLoader
extends RefCounted

## Manages loading and parsing of all game data files.
## This includes quests, dialogues, characters, items, and world data.
## All functions are static and operate on file paths to load data.

static var _test_data: Dictionary = {}

static func set_test_data(id: String, data: Dictionary) -> void:
	_test_data[id] = data

static func clear_test_data() -> void:
	_test_data.clear()

static func get_quest(quest_id: String) -> Dictionary:
	if _test_data.has(quest_id):
		return _test_data[quest_id]

	var path = "res://data/quests/" + quest_id + ".json"
	if not FileAccess.file_exists(path):
		# Fallback for placeholder quests
		if quest_id == "report_to_rebel_leader":
			return {
				"id": "report_to_rebel_leader",
				"act": 1,
				"location": "rebel_hideout",
				"prerequisites": [{"completed": "rescue_prisoner"}],
				"approaches": {},
				"outcomes": {}
			}
		return {}

	var file = FileAccess.open(path, FileAccess.READ)
	if not file:
		push_error("Failed to open file: " + path)
		return {}

	var content = file.get_as_text()
	var json = JSON.parse_string(content)
	
	if typeof(json) != TYPE_DICTIONARY:
		push_error("Invalid JSON in quest file: " + path)
		return {}
		
	return json


static func get_thought(thought_id: String) -> Dictionary:
	if _test_data.has(thought_id):
		return _test_data[thought_id]

	var path = "res://data/thoughts/" + thought_id + ".json"
	if not FileAccess.file_exists(path):
		push_warning("Thought file not found: " + path)
		return {}

	var file = FileAccess.open(path, FileAccess.READ)
	if not file:
		push_error("Failed to open file: " + path)
		return {}

	var content = file.get_as_text()
	var json = JSON.parse_string(content)
	
	if typeof(json) != TYPE_DICTIONARY:
		push_error("Invalid JSON in thought file: " + path)
		return {}
		
	return json
