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

	var path = "res://data/quests/" + quest_id + ".md"
	if not FileAccess.file_exists(path):
		# Fallback for testing non-existent quests or placeholder
		if quest_id == "report_to_rebel_leader":  # Keep placeholder for now
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
	return _parse_frontmatter(content)


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


static func _parse_frontmatter(content: String) -> Dictionary:
	var lines = content.split("\n")
	var yaml_lines: Array[String] = []
	var found_start = false

	for line in lines:
		if line.strip_edges() == "---":
			if not found_start:
				found_start = true
				continue
			else:
				break  # End of frontmatter
		if found_start:
			yaml_lines.append(line)

	return _parse_yaml(yaml_lines)


## Simple recursive YAML parser for frontmatter subset.
## Supports: Nested dicts (indentation), inline JSON-like lists/dicts, simple key-values.
static func _parse_yaml(lines: Array[String]) -> Dictionary:
	var result = {}
	var stack = [{"node": result, "indent": -1}]

	for line in lines:
		if line.strip_edges().is_empty() or line.strip_edges().begins_with("#"):
			continue

		var indent = line.length() - line.strip_edges(true).length()
		var content = line.strip_edges()

		# Pop stack until we find the parent
		while stack.size() > 1 and indent <= stack.back()["indent"]:
			stack.pop_back()

		var parent = stack.back()["node"]

		if content.ends_with(":"):
			# Block key (start of object)
			var key = content.trim_suffix(":")
			var new_obj = {}
			parent[key] = new_obj
			stack.push_back({"node": new_obj, "indent": indent})

		elif ": " in content:
			# Key-value pair
			var parts = content.split(": ", true, 1)
			var key = parts[0]
			var value_str = parts[1]
			parent[key] = _parse_value(value_str)

	return result


static func _parse_value(val_str: String) -> Variant:
	val_str = val_str.strip_edges()

	# Integer
	if val_str.is_valid_int():
		return val_str.to_int()
	# Float
	if val_str.is_valid_float() and "." in val_str:
		return val_str.to_float()
	# Boolean
	if val_str == "true":
		return true
	if val_str == "false":
		return false

	# Inline List [a, b]
	if val_str.begins_with("[") and val_str.ends_with("]"):
		var inner = val_str.substr(1, val_str.length() - 2)
		if inner.is_empty():
			return []
		# Simple split by comma (fails on nested commas, but sufficient for simple lists)
		var items = []
		for item in inner.split(","):
			items.append(_parse_value(item.strip_edges().trim_prefix('"').trim_suffix('"')))
		return items

	# Inline Dict {a: b} - Minimal support
	if val_str.begins_with("{") and val_str.ends_with("}"):
		var inner = val_str.substr(1, val_str.length() - 2)
		var parts = inner.split(":", true, 1)
		if parts.size() == 2:
			var key = parts[0].strip_edges().trim_prefix('"').trim_suffix('"')
			var val = _parse_value(parts[1])
			return {key: val}
		return {}

	# String (remove quotes if present)
	if val_str.begins_with('"') and val_str.ends_with('"'):
		return val_str.substr(1, val_str.length() - 2)

	return val_str
