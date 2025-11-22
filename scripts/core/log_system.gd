# scripts/core/log_system.gd
extends Node

## Logging system for playtest debugging. Replaces quest trigger spam
## with event-driven, filterable logging that supports replay analysis.
##
## Example usage:
##   var log = LogSystem.new()
##   log.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST,
##       "quest_completed", {"quest_id": "join_rebels", "approach": "diplomatic"})

enum Level { DEBUG = 0, INFO = 1, WARN = 2, ERROR = 3 }
enum Category { QUEST, DIALOGUE, DEGRADATION, WORLD, PLAYER, COMBAT }

## Configuration dictionary - modify to control logging behavior
var config: Dictionary = {
	"enabled": true,
	"min_level": Level.INFO,
	"categories": [],  # Empty = log all categories
	"write_to_file": false,
	"file_path": "user://playtest_log.txt",
	"batch_size": 100,  # Batch writes to file
}

## Internal storage of log entries
var _logs: Array[Dictionary] = []

## Previous state snapshot for diffing
var _previous_state: Dictionary = {}

## Batch write counter
var _write_counter: int = 0


## Connect to GameState to monitor state changes. Call this after LogSystem is instantiated.
func connect_to_game_state() -> void:
	if GameState:
		GameState.state_changed.connect(_on_state_changed)


func _on_state_changed(new_state: Dictionary) -> void:
	"""Called when GameState emits state_changed signal.
	Diffs new_state against _previous_state and logs changes."""
	if not config["enabled"]:
		return

	# Diff states and log changes
	var changes = _diff_states(_previous_state, new_state)
	if not changes.is_empty():
		for change in changes:
			# Determine appropriate log level based on change type
			var level = _level_for_change(change)
			var category = _category_for_change(change)

			# Check if this log should be filtered
			if _should_log(level, category):
				add_log_entry(level, category, change.get("event", "state_change"), change.get("details", {}))

	# Update previous state
	_previous_state = new_state.duplicate(true)


func add_log_entry(level: int, category: int, event: String, details: Dictionary = {}) -> void:
	"""Log an event with specified level, category, and details.

	Args:
		level: One of Level.DEBUG, INFO, WARN, ERROR
		category: One of Category.QUEST, DIALOGUE, DEGRADATION, WORLD, PLAYER, COMBAT
		event: Name of the event (e.g., "quest_completed", "stat_degraded")
		details: Dictionary of event-specific data"""

	if not config["enabled"]:
		return

	# Check if this log should be filtered
	if not _should_log(level, category):
		return

	var log_entry: Dictionary = {
		"timestamp": Time.get_ticks_msec(),
		"level": level,
		"level_name": Level.keys()[level],
		"category": category,
		"category_name": Category.keys()[category],
		"event": event,
		"details": details,
	}

	_logs.append(log_entry)

	# Print to console with formatting
	_print_log_entry(log_entry)

	# Check if we should batch-write to file
	if config["write_to_file"]:
		_write_counter += 1
		if _write_counter >= config["batch_size"]:
			_flush_to_file()


func export_logs() -> String:
	"""Export all logs as JSON string for external analysis."""
	return JSON.stringify(_logs, "\t", true)


func export_logs_to_file() -> void:
	"""Export all logs to file and clear internal buffer."""
	_flush_to_file()


func clear_logs() -> void:
	"""Clear all logs from memory."""
	_logs.clear()
	_write_counter = 0


func get_logs() -> Array[Dictionary]:
	"""Get all logged entries. Returns copy to prevent external mutation."""
	var copy: Array[Dictionary] = []
	for entry in _logs:
		copy.append(entry.duplicate(true))
	return copy


func set_enabled(enabled: bool) -> void:
	"""Enable or disable logging."""
	config["enabled"] = enabled


func set_min_level(level: int) -> void:
	"""Set minimum log level to output."""
	config["min_level"] = level


func set_categories(categories: Array) -> void:
	"""Set which categories to log. Empty array = all categories."""
	config["categories"] = categories


func set_write_to_file(enabled: bool) -> void:
	"""Enable or disable file writing."""
	config["write_to_file"] = enabled


## ============================================================================
## PRIVATE METHODS
## ============================================================================


func _should_log(level: int, category: int) -> bool:
	"""Check if this log entry should be output based on filters."""
	# Check level
	if level < config["min_level"]:
		return false

	# Check category filter (empty = all)
	if config["categories"].size() > 0 and not config["categories"].has(category):
		return false

	return true


func _diff_states(old_state: Dictionary, new_state: Dictionary) -> Array[Dictionary]:
	"""Compare two states and return list of changes detected.
	Returns array of change dictionaries with event and details."""

	var changes: Array[Dictionary] = []

	# Shallow diff first to catch major changes
	if old_state.is_empty():
		# Initial state - log as initialization
		(
			changes
			. append(
				{
					"event": "state_initialized",
					"details": {},
				}
			)
		)
		return changes

	# Deep diff for key sections
	_deep_diff_section(old_state.get("quests", {}), new_state.get("quests", {}), "quests", changes)
	_deep_diff_section(old_state.get("player", {}), new_state.get("player", {}), "player", changes)
	_deep_diff_section(old_state.get("world", {}), new_state.get("world", {}), "world", changes)
	_deep_diff_section(old_state.get("meta", {}), new_state.get("meta", {}), "meta", changes)

	return changes


func _deep_diff_section(
	old_section: Dictionary,
	new_section: Dictionary,
	section_name: String,
	changes: Array[Dictionary]
) -> void:
	"""Recursively diff a section of state and record changes."""

	# Check for new or modified keys
	for key in new_section.keys():
		if not old_section.has(key):
			(
				changes
				. append(
					{
						"event": "%s_added" % section_name,
						"details": {"key": key, "value": new_section[key]},
					}
				)
			)
		elif old_section[key] != new_section[key]:
			# For nested structures, continue diffing
			if typeof(new_section[key]) == TYPE_DICTIONARY:
				_deep_diff_section(
					old_section[key], new_section[key], "%s_%s" % [section_name, key], changes
				)
			else:
				(
					changes
					. append(
						{
							"event": "%s_changed" % section_name,
							"details":
							{
								"key": key,
								"old_value": old_section[key],
								"new_value": new_section[key]
							},
						}
					)
				)

	# Check for removed keys
	for key in old_section.keys():
		if not new_section.has(key):
			(
				changes
				. append(
					{
						"event": "%s_removed" % section_name,
						"details": {"key": key, "value": old_section[key]},
					}
				)
			)


func _level_for_change(change: Dictionary) -> int:
	"""Determine log level for a detected change."""
	var event: String = change.get("event", "")

	if "degradation" in event or "removed" in event or "failed" in event:
		return Level.WARN
	if "error" in event or "invalid" in event:
		return Level.ERROR
	return Level.INFO


func _category_for_change(change: Dictionary) -> int:
	"""Determine log category for a detected change."""
	var event: String = change.get("event", "")

	# Check event keywords to classify category
	var category_keywords = {
		Category.DIALOGUE: ["dialogue", "timeline"],
		Category.DEGRADATION: ["flexibility", "conviction"],
		Category.WORLD: ["npc", "location", "world"],
		Category.PLAYER: ["player", "position", "health"],
		Category.COMBAT: ["combat", "enemy"],
	}

	for category in category_keywords:
		var keywords: Array = category_keywords[category]
		for keyword in keywords:
			if keyword in event:
				return category
	return Category.QUEST


func _print_log_entry(entry: Dictionary) -> void:
	"""Format and print a log entry to console.

	Console output is human-readable, full JSON stored in entry for file export.
	This allows debugging logs to be clear while preserving structured data."""
	var level_name = entry["level_name"]
	var category_name = entry["category_name"]
	var event = entry["event"]
	var details = entry["details"]

	# Build human-readable console output
	var console_msg = "[%s] [%s] %s" % [level_name, category_name, event]

	# Add human-readable details based on event type
	if event == "quest_timeline_started" and not details.is_empty():
		console_msg += " | Started quest: %s (timeline: %s)" % [
			details.get("quest_id", "?"),
			details.get("timeline_id", "?")
		]
	elif event == "quest_locked" and not details.is_empty():
		console_msg += " | Quest locked: %s (%s)" % [
			details.get("quest_id", "?"),
			details.get("reason", "?")
		]
	elif event == "quest_trigger_in_range" and not details.is_empty():
		var locked_status = "unlocked" if not details.get("locked", false) else "locked"
		console_msg += " | Quest trigger in range: %s (%s)" % [
			details.get("quest_id", "?"),
			locked_status
		]
	elif event == "quest_trigger_initialized" and not details.is_empty():
		console_msg += " | Quest trigger initialized: %s" % details.get("quest_id", "?")
	elif event == "quest_trigger_removed" and not details.is_empty():
		console_msg += " | Quest trigger removed: %s (%s)" % [
			details.get("quest_id", "?"),
			details.get("reason", "?")
		]
	elif event == "quest_auto_completed_debug" and not details.is_empty():
		console_msg += " | DEBUG: Auto-completed quest: %s (approach: %s)" % [
			details.get("quest_id", "?"),
			details.get("approach", "?")
		]
	elif not details.is_empty():
		# Fallback: Include JSON for unknown event types (preserves backward compatibility)
		console_msg += " | " + JSON.stringify(details)

	print(console_msg)


func _flush_to_file() -> void:
	"""Write accumulated logs to file."""
	if _logs.is_empty():
		return

	var file = FileAccess.open(config["file_path"], FileAccess.WRITE)
	if file == null:
		push_error("Failed to open log file: " + config["file_path"])
		return

	# Write JSON array of logs
	var json_str = JSON.stringify(_logs, "\t", true)
	file.store_string(json_str)

	_write_counter = 0
	print("Logs flushed to file: " + config["file_path"])
