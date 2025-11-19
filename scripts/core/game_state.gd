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
