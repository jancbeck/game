extends Node

signal state_changed(new_state: Dictionary)

var state: Dictionary:
	get:
		return _state.duplicate(true)
var _state: Dictionary = {}


func _ready() -> void:
	_initialize_state()


func _initialize_state() -> void:
	_state = {
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
		"world": {"current_location": "", "act": 1, "npc_states": {}, "location_flags": {}},
		"quests":
		{
			"join_rebels":
			{"status": "available", "approach_taken": "", "objectives_completed": []}
		},
		"dialogue_vars": {},
		"combat": {"active": false, "enemies": [], "available_abilities": []},
		"meta": {"playtime_seconds": 0, "save_version": "1.0", "current_scene": ""}
	}
	# Emit initial state
	call_deferred("emit_signal", "state_changed", _state.duplicate(true))


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_F5:
			SaveSystem.save_state(_state)
			get_viewport().set_input_as_handled()
		elif event.keycode == KEY_F9:
			var loaded_state = SaveSystem.load_state()
			if not loaded_state.is_empty():
				_state = loaded_state
				# Reload current scene to ensure nodes (like QuestTriggers) match the new state
				# e.g. Triggers that were deleted in the save should not be present, 
				# or Triggers that exist in the save but were deleted in the current session reappear.
				get_tree().reload_current_scene()
				state_changed.emit(_state.duplicate(true))
			get_viewport().set_input_as_handled()


func reset() -> void:
	_initialize_state()


## Dispatches an action through a reducer.
## The reducer function should have the signature: (state: Dictionary) -> Dictionary
## or (state: Dictionary, ...) -> Dictionary if arguments are bound.
func dispatch(reducer: Callable) -> void:
	var new_state = reducer.call(_state)

	# Simple validation to ensure we received a dictionary back
	if typeof(new_state) != TYPE_DICTIONARY:
		push_error("Reducer returned invalid state type")
		return

	# Check for changes before updating and emitting
	# Note: Deep comparison can be expensive for very large states, 
	# but essential to prevent spam for things that run every frame like movement.
	if new_state.hash() != _state.hash():
		_state = new_state
		state_changed.emit(_state.duplicate(true))
