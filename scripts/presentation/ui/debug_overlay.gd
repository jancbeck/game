extends CanvasLayer

enum DisplayMode { STATE_ONLY, LOGS_ONLY, BOTH }  ## Debug overlay display mode

@onready var label: RichTextLabel = $RichTextLabel

var _display_mode: int = DisplayMode.STATE_ONLY  # noqa: class-definitions-order
var _show_logs: bool = false  # noqa: class-definitions-order


func _ready():
	GameState.state_changed.connect(_on_state_changed)
	_on_state_changed(GameState.state)

	# Enable input handling for debug shortcuts
	set_process_input(true)


func _on_state_changed(state: Dictionary):
	_update_display(state)


func _format_log_message(log_entry: Dictionary) -> String:
	"""Format log message intelligently based on event type."""
	var event = log_entry.get("event", "unknown")
	var details = log_entry.get("details", {})

	match event:
		"quest_timeline_started":
			var quest_id = details.get("quest_id", "unknown")
			return "Started: %s" % quest_id
		_:
			return event


func _update_display(state: Dictionary):
	"""Update the debug overlay display based on current mode."""
	var text_parts: Array[String] = []

	# Add state information if in STATE_ONLY or BOTH mode
	if _display_mode == DisplayMode.STATE_ONLY or _display_mode == DisplayMode.BOTH:
		var flexibility_str = JSON.stringify(state["player"]["flexibility"], "\t", true)
		var convictions_str = JSON.stringify(state["player"]["convictions"], "\t", true)
		text_parts.append(
			"Flexibility:\n" + flexibility_str + "\n\nConvictions:\n" + convictions_str
		)

	# Add logs if in LOGS_ONLY or BOTH mode
	if _display_mode == DisplayMode.LOGS_ONLY or _display_mode == DisplayMode.BOTH:
		var logs = LogSystem.get_logs()
		if not logs.is_empty():
			var recent_logs = logs.slice(-10)  # Show last 10 logs
			var logs_text = "\n[RECENT LOGS]\n"
			for log_entry in recent_logs:
				var formatted_message = _format_log_message(log_entry)
				logs_text += (
					"[%s] %s: %s\n"
					% [log_entry["level_name"], log_entry["category_name"], formatted_message]
				)
			text_parts.append(logs_text)
		else:
			text_parts.append("\n[RECENT LOGS]\n(No logs yet)")

	# Add help text
	text_parts.append("\n[DEBUG CONTROLS]\nF7: Toggle log display\nL: Clear logs\nE: Export logs")

	label.set_text("\n".join(text_parts))


func _input(event: InputEvent):
	"""Handle debug input for logging controls."""
	if event is InputEventKey and event.pressed:
		match event.keycode:
			KEY_F7:
				# Toggle between STATE_ONLY, LOGS_ONLY, BOTH, STATE_ONLY...
				_display_mode = (_display_mode + 1) % 3
				_update_display(GameState.state)
				print("Debug display mode: %d" % _display_mode)
				get_viewport().set_input_as_handled()

			KEY_L:
				# Clear logs
				LogSystem.clear_logs()
				print("Logs cleared")
				_update_display(GameState.state)
				get_viewport().set_input_as_handled()

			KEY_E:
				# Export logs to file
				LogSystem.set_write_to_file(true)
				LogSystem.export_logs_to_file()
				print("Logs exported to: %s" % LogSystem.config["file_path"])
				get_viewport().set_input_as_handled()
