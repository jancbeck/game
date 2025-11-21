extends Node

## Bridge between Dialogic 2 and GameState architecture.
## Manages Dialogic timeline lifecycle and maps Dialogic events to GameStateActions.
## This should be instantiated in the main scene or added as an autoload.

var _current_timeline_id: String = ""


func _ready() -> void:
	# Connect to Dialogic 2 signals
	# Based on Dialogic 2 API (will verify exact signal names)
	if Dialogic.timeline_ended.connect(_on_timeline_ended) != OK:
		push_warning("DialogSystem: Failed to connect to Dialogic.timeline_ended")

	if Dialogic.signal_event.connect(_on_dialogic_signal) != OK:
		push_warning("DialogSystem: Failed to connect to Dialogic.signal_event")


## Starts a Dialogic timeline and updates GameState meta to track it
func start_timeline(timeline_id: String) -> void:
	if timeline_id.is_empty():
		push_error("DialogSystem: Cannot start timeline with empty ID")
		return

	_current_timeline_id = timeline_id

	# Update GameState to reflect active timeline
	GameState.dispatch(func(state):
		var new_state = state.duplicate(true)
		if not new_state.has("meta"):
			new_state["meta"] = {}
		new_state["meta"]["active_dialog_timeline"] = timeline_id
		return new_state
	)

	# Start the timeline via Dialogic API
	Dialogic.start(timeline_id)


## Called when a Dialogic timeline ends
func _on_timeline_ended() -> void:
	if _current_timeline_id.is_empty():
		return

	var ended_id = _current_timeline_id
	_current_timeline_id = ""

	# Clear active timeline from GameState
	GameState.dispatch(func(state):
		var new_state = state.duplicate(true)
		if new_state.has("meta") and typeof(new_state["meta"]) == TYPE_DICTIONARY:
			new_state["meta"]["active_dialog_timeline"] = ""
		return new_state
	)

	print("DialogSystem: Timeline '%s' ended" % ended_id)


## Maps Dialogic signal events to GameStateActions
## Signal format examples:
##   "start_quest:join_rebels"
##   "complete_quest:join_rebels:diplomatic"
##   "modify_conviction:violence_thoughts:2"
##   "modify_flexibility:charisma:-3"
func _on_dialogic_signal(argument: String) -> void:
	print("DialogSystem: Received signal '%s'" % argument)

	var parts = argument.split(":", false)
	if parts.is_empty():
		push_warning("DialogSystem: Empty signal argument")
		return

	var command = parts[0]

	match command:
		"start_quest":
			if parts.size() >= 2:
				GameStateActions.start_quest(parts[1])
			else:
				push_error("DialogSystem: 'start_quest' requires quest_id")

		"complete_quest":
			if parts.size() >= 3:
				GameStateActions.complete_quest(parts[1], parts[2])
			elif parts.size() >= 2:
				GameStateActions.complete_quest(parts[1])
			else:
				push_error("DialogSystem: 'complete_quest' requires quest_id")

		"modify_conviction":
			if parts.size() >= 3:
				var conviction_name = parts[1]
				var amount = parts[2].to_int()
				GameStateActions.modify_conviction(conviction_name, amount)
			else:
				push_error("DialogSystem: 'modify_conviction' requires conviction_name and amount")

		"modify_flexibility":
			if parts.size() >= 3:
				var stat_name = parts[1]
				var amount = parts[2].to_int()
				GameStateActions.modify_flexibility(stat_name, amount)
			else:
				push_error("DialogSystem: 'modify_flexibility' requires stat_name and amount")

		_:
			push_warning("DialogSystem: Unknown signal command '%s'" % command)
