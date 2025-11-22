class_name TestLogSystem  # noqa: max-public-methods
extends GdUnitTestSuite

# Enums copied from LogSystem for testing
class LogSystemEnums:
	enum Level { DEBUG = 0, INFO = 1, WARN = 2, ERROR = 3 }
	enum Category { QUEST, DIALOGUE, DEGRADATION, WORLD, PLAYER, COMBAT }

var log_system: Node
var initial_state: Dictionary
var level = LogSystemEnums.Level
var category = LogSystemEnums.Category


func before_test():
	# Create LogSystem instance (it's a Node, so we create a new one for each test)
	log_system = Node.new()
	log_system.set_script(load("res://scripts/core/log_system.gd"))
	add_child(log_system)

	# Initialize test state
	initial_state = {
		"player":
		{
			"position": Vector3.ZERO,
			"health": 100,
			"max_health": 100,
			"flexibility": {"charisma": 10, "cunning": 10, "empathy": 10},
			"convictions": {"violence_thoughts": 0, "deceptive_acts": 0, "compassionate_acts": 0},
			"inventory": [],
			"equipment": {"weapon": "", "armor": ""}
		},
		"world":
		{
			"current_location": "",
			"act": 1,
			"npc_states": {},
			"location_flags": {},
			"memory_flags": []
		},
		"quests":
		{"join_rebels": {"status": "available", "approach_taken": "", "objectives_completed": []}},
		"dialogue_vars": {},
		"combat": {"active": false, "enemies": [], "available_abilities": []},
		"meta":
		{
			"playtime_seconds": 0,
			"save_version": "1.0",
			"current_scene": "",
			"active_dialog_timeline": "",
			"active_thought": ""
		},
		"dialogic": {"vars": {}, "engine_state": {}}
	}


func after_test():
	# Clean up orphan nodes
	if log_system and not log_system.is_queued_for_deletion():
		log_system.queue_free()


func test_log_system_is_enabled_by_default():
	# Assert
	assert_that(log_system.config["enabled"]).is_true()


func test_log_method_adds_entry():
	# Act
	log_system.add_log_entry(
		level.INFO, category.QUEST, "test_event", {"test_key": "test_value"}
	)

	# Assert
	var logs = log_system.get_logs()
	assert_that(logs).has_size(1)
	assert_that(logs[0]["event"]).is_equal("test_event")
	assert_that(logs[0]["details"]["test_key"]).is_equal("test_value")


func test_log_respects_min_level_filter():
	# Arrange
	log_system.set_min_level(LogSystem.Level.WARN)

	# Act - Log at INFO level (should be filtered)
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "info_event", {})

	# Act - Log at WARN level (should be added)
	log_system.add_log_entry(LogSystem.Level.WARN, LogSystem.Category.QUEST, "warn_event", {})

	# Assert
	var logs = log_system.get_logs()
	assert_that(logs).has_size(1)
	assert_that(logs[0]["event"]).is_equal("warn_event")


func test_log_respects_category_filter():
	# Arrange
	log_system.set_categories([LogSystem.Category.QUEST])

	# Act - Log QUEST (should be added)
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "quest_event", {})

	# Act - Log DIALOGUE (should be filtered)
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.DIALOGUE, "dialogue_event", {})

	# Assert
	var logs = log_system.get_logs()
	assert_that(logs).has_size(1)
	assert_that(logs[0]["event"]).is_equal("quest_event")


func test_log_disabled_prevents_logging():
	# Arrange
	log_system.set_enabled(false)

	# Act
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "test_event", {})

	# Assert
	var logs = log_system.get_logs()
	assert_that(logs).has_size(0)


func test_log_entry_contains_timestamp():
	# Act
	var before_time = Time.get_ticks_msec()
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "test_event", {})
	var after_time = Time.get_ticks_msec()

	# Assert
	var logs = log_system.get_logs()
	var timestamp = logs[0]["timestamp"]
	assert_that(timestamp >= before_time).is_true()
	assert_that(timestamp <= after_time).is_true()


func test_log_entry_contains_level_name():
	# Act
	log_system.add_log_entry(LogSystem.Level.ERROR, LogSystem.Category.QUEST, "test_event", {})

	# Assert
	var logs = log_system.get_logs()
	assert_that(logs[0]["level"]).is_equal(LogSystem.Level.ERROR)
	assert_that(logs[0]["level_name"]).is_equal("ERROR")


func test_log_entry_contains_category_name():
	# Act
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.DEGRADATION, "test_event", {})

	# Assert
	var logs = log_system.get_logs()
	assert_that(logs[0]["category"]).is_equal(LogSystem.Category.DEGRADATION)
	assert_that(logs[0]["category_name"]).is_equal("DEGRADATION")


func test_get_logs_returns_copy():
	# Arrange
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "test_event", {})

	# Act
	var logs1 = log_system.get_logs()
	var logs2 = log_system.get_logs()

	# Assert
	assert_that(logs1).is_not_same(logs2)


func test_clear_logs_removes_all_entries():
	# Arrange
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "event1", {})
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "event2", {})

	# Act
	log_system.clear_logs()

	# Assert
	var logs = log_system.get_logs()
	assert_that(logs).is_empty()


func test_export_logs_returns_json_string():
	# Arrange
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "test_event", {"key": "value"})

	# Act
	var json_str = log_system.export_logs()

	# Assert
	assert_that(json_str).contains("test_event")
	assert_that(json_str).contains("key")
	assert_that(json_str).contains("value")


func test_multiple_logs_preserve_order():
	# Act
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "first", {})
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "second", {})
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "third", {})

	# Assert
	var logs = log_system.get_logs()
	assert_that(logs[0]["event"]).is_equal("first")
	assert_that(logs[1]["event"]).is_equal("second")
	assert_that(logs[2]["event"]).is_equal("third")


func test_empty_category_filter_logs_all_categories():
	# Arrange
	log_system.set_categories([])  # Empty = all categories

	# Act
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "event1", {})
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.DIALOGUE, "event2", {})
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.DEGRADATION, "event3", {})

	# Assert
	var logs = log_system.get_logs()
	assert_that(logs).has_size(3)


func test_multiple_category_filter():
	# Arrange
	log_system.set_categories([LogSystem.Category.QUEST, LogSystem.Category.WORLD])

	# Act
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "quest_event", {})
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.WORLD, "world_event", {})
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.DIALOGUE, "dialogue_event", {})

	# Assert
	var logs = log_system.get_logs()
	assert_that(logs).has_size(2)
	var events = [logs[0]["event"], logs[1]["event"]]
	assert_that(events).contains("quest_event")
	assert_that(events).contains("world_event")


func test_diff_states_detects_new_quest():
	# Arrange
	var old_state = initial_state.duplicate(true)
	var new_state = initial_state.duplicate(true)
	new_state["quests"]["new_quest"] = {
		"status": "available", "approach_taken": "", "objectives_completed": []
	}

	# Act
	var changes = log_system._diff_states(old_state, new_state)

	# Assert
	assert_that(changes).is_not_empty()
	var event_names = changes.map(func(c): return c.get("event", ""))
	assert_that(event_names).contains("quests_added")


func test_diff_states_detects_quest_status_change():
	# Arrange
	var old_state = initial_state.duplicate(true)
	var new_state = initial_state.duplicate(true)
	new_state["quests"]["join_rebels"]["status"] = "active"

	# Act
	var changes = log_system._diff_states(old_state, new_state)

	# Assert
	assert_that(changes).is_not_empty()


func test_diff_states_detects_flexibility_change():
	# Arrange
	var old_state = initial_state.duplicate(true)
	var new_state = initial_state.duplicate(true)
	new_state["player"]["flexibility"]["charisma"] = 8

	# Act
	var changes = log_system._diff_states(old_state, new_state)

	# Assert
	assert_that(changes).is_not_empty()


func test_diff_states_empty_old_state_logs_initialization():
	# Arrange
	var old_state = {}
	var new_state = initial_state.duplicate(true)

	# Act
	var changes = log_system._diff_states(old_state, new_state)

	# Assert
	assert_that(changes).is_not_empty()
	assert_that(changes[0]["event"]).is_equal("state_initialized")


func test_diff_states_no_change_returns_empty():
	# Arrange
	var old_state = initial_state.duplicate(true)
	var new_state = initial_state.duplicate(true)

	# Act
	var changes = log_system._diff_states(old_state, new_state)

	# Assert
	assert_that(changes).has_size(0)


func test_level_for_change_warns_on_degradation():
	# Act
	var level = log_system._level_for_change({"event": "player_degradation"})

	# Assert
	assert_that(level).is_equal(LogSystem.Level.WARN)


func test_level_for_change_errors_on_invalid():
	# Act
	var level = log_system._level_for_change({"event": "invalid_action"})

	# Assert
	assert_that(level).is_equal(LogSystem.Level.ERROR)


func test_level_for_change_info_on_normal():
	# Act
	var level = log_system._level_for_change({"event": "quest_completed"})

	# Assert
	assert_that(level).is_equal(LogSystem.Level.INFO)


func test_category_for_change_identifies_quest_events():
	# Act
	var category = log_system._category_for_change({"event": "quest_started"})

	# Assert
	assert_that(category).is_equal(LogSystem.Category.QUEST)


func test_category_for_change_identifies_dialogue_events():
	# Act
	var category = log_system._category_for_change({"event": "dialogue_choice_made"})

	# Assert
	assert_that(category).is_equal(LogSystem.Category.DIALOGUE)


func test_category_for_change_identifies_degradation_events():
	# Act
	var category = log_system._category_for_change({"event": "flexibility_degraded"})

	# Assert
	assert_that(category).is_equal(LogSystem.Category.DEGRADATION)


func test_category_for_change_identifies_player_events():
	# Act
	var category = log_system._category_for_change({"event": "player_health_changed"})

	# Assert
	assert_that(category).is_equal(LogSystem.Category.PLAYER)


func test_config_fields_are_mutable():
	# Act
	log_system.config["min_level"] = LogSystem.Level.ERROR
	log_system.config["enabled"] = false

	# Assert
	assert_that(log_system.config["min_level"]).is_equal(LogSystem.Level.ERROR)
	assert_that(log_system.config["enabled"]).is_false()


func test_log_entry_preserves_details_dictionary():
	# Arrange
	var details = {"quest_id": "join_rebels", "approach": "diplomatic", "difficulty": 5}

	# Act
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "quest_completed", details)

	# Assert
	var logs = log_system.get_logs()
	assert_that(logs[0]["details"]).is_equal(details)


func test_set_enabled_true_allows_logging():
	# Arrange
	log_system.set_enabled(false)
	log_system.set_enabled(true)

	# Act
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "test_event", {})

	# Assert
	var logs = log_system.get_logs()
	assert_that(logs).is_not_empty()


func test_set_min_level_affects_filtering():
	# Arrange
	log_system.set_min_level(LogSystem.Level.DEBUG)

	# Act
	log_system.add_log_entry(LogSystem.Level.DEBUG, LogSystem.Category.QUEST, "debug_event", {})

	# Assert
	var logs = log_system.get_logs()
	assert_that(logs).is_not_empty()


func test_should_log_respects_all_filters():
	# Arrange
	log_system.set_enabled(false)
	log_system.set_min_level(LogSystem.Level.WARN)
	log_system.set_categories([LogSystem.Category.QUEST])

	# Act - attempt to log at INFO level with DIALOGUE category while disabled
	var should_log = log_system._should_log(LogSystem.Level.INFO, LogSystem.Category.DIALOGUE)

	# Assert - all three reasons to skip should result in false
	assert_that(should_log).is_false()

	# Re-enable and check again
	log_system.set_enabled(true)
	should_log = log_system._should_log(LogSystem.Level.INFO, LogSystem.Category.DIALOGUE)
	assert_that(should_log).is_false()  # Still false due to level and category


## File I/O Tests

func test_flush_to_file_writes_logs_as_json():
	# Arrange
	var test_file = "user://test_log.txt"
	log_system.config["file_path"] = test_file
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "test_event", {"key": "value"})

	# Cleanup existing file
	var dir = DirAccess.open("user://")
	if dir and dir.file_exists("test_log.txt"):
		dir.remove("test_log.txt")

	# Act
	log_system._flush_to_file()

	# Assert - file exists
	dir = DirAccess.open("user://")
	assert_that(dir and dir.file_exists("test_log.txt")).is_true()

	# Assert - file contains valid JSON
	var file = FileAccess.open(test_file, FileAccess.READ)
	assert_that(file).is_not_null()
	var content = file.get_as_text()
	var json = JSON.new()
	var parse_result = json.parse(content)
	assert_that(parse_result == OK).is_true()

	# Cleanup
	dir = DirAccess.open("user://")
	if dir:
		dir.remove("test_log.txt")


func test_flush_to_file_contains_all_log_entries():
	# Arrange
	var test_file = "user://test_log_all.txt"
	log_system.config["file_path"] = test_file
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "event1", {})
	log_system.add_log_entry(LogSystem.Level.WARN, LogSystem.Category.DIALOGUE, "event2", {})

	# Cleanup existing file
	var dir = DirAccess.open("user://")
	if dir and dir.file_exists("test_log_all.txt"):
		dir.remove("test_log_all.txt")

	# Act
	log_system._flush_to_file()

	# Assert - file contains both events
	var file = FileAccess.open(test_file, FileAccess.READ)
	var content = file.get_as_text()
	assert_that(content).contains("event1")
	assert_that(content).contains("event2")

	# Cleanup
	dir = DirAccess.open("user://")
	if dir:
		dir.remove("test_log_all.txt")


func test_flush_to_file_resets_write_counter():
	# Arrange
	var test_file = "user://test_log_counter.txt"
	log_system.config["file_path"] = test_file
	log_system.config["write_to_file"] = true
	log_system.config["batch_size"] = 2

	# Cleanup existing file
	var dir = DirAccess.open("user://")
	if dir and dir.file_exists("test_log_counter.txt"):
		dir.remove("test_log_counter.txt")

	# Act - add one entry (counter = 1)
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "event1", {})
	var counter_before = log_system._write_counter

	# Flush and check counter is reset
	log_system._flush_to_file()

	# Assert
	assert_that(counter_before).is_equal(1)
	assert_that(log_system._write_counter).is_equal(0)

	# Cleanup
	dir = DirAccess.open("user://")
	if dir:
		dir.remove("test_log_counter.txt")


func test_flush_to_file_handles_empty_logs():
	# Arrange
	var test_file = "user://test_log_empty.txt"
	log_system.config["file_path"] = test_file

	# Cleanup existing file
	var dir = DirAccess.open("user://")
	if dir and dir.file_exists("test_log_empty.txt"):
		dir.remove("test_log_empty.txt")

	# Act - flush with no logs
	log_system._flush_to_file()

	# Assert - file should not be created for empty logs
	dir = DirAccess.open("user://")
	assert_that(not (dir and dir.file_exists("test_log_empty.txt"))).is_true()


func test_export_logs_to_file_calls_flush():
	# Arrange
	var test_file = "user://test_log_export.txt"
	log_system.config["file_path"] = test_file
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "test_event", {})

	# Cleanup existing file
	var dir = DirAccess.open("user://")
	if dir and dir.file_exists("test_log_export.txt"):
		dir.remove("test_log_export.txt")

	# Act
	log_system.export_logs_to_file()

	# Assert - file exists
	dir = DirAccess.open("user://")
	assert_that(dir and dir.file_exists("test_log_export.txt")).is_true()

	# Cleanup
	dir = DirAccess.open("user://")
	if dir:
		dir.remove("test_log_export.txt")


func test_flush_to_file_formats_json_correctly():
	# Arrange
	var test_file = "user://test_log_format.txt"
	log_system.config["file_path"] = test_file
	log_system.add_log_entry(LogSystem.Level.INFO, LogSystem.Category.QUEST, "test", {"nested": {"key": "value"}})

	# Cleanup existing file
	var dir = DirAccess.open("user://")
	if dir and dir.file_exists("test_log_format.txt"):
		dir.remove("test_log_format.txt")

	# Act
	log_system._flush_to_file()

	# Assert - file contains properly formatted JSON
	var file = FileAccess.open(test_file, FileAccess.READ)
	var content = file.get_as_text()

	# JSON should be indented (pretty-printed)
	assert_that(content).contains("\t")

	# Should be valid JSON array
	var json = JSON.new()
	assert_that(json.parse(content) == OK).is_true()
	assert_that(json.data is Array).is_true()

	# Cleanup
	dir = DirAccess.open("user://")
	if dir:
		dir.remove("test_log_format.txt")
