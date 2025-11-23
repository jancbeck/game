extends Node

signal state_changed(new_state: Dictionary)

const SaveSystem = preload("res://scripts/core/save_system.gd")

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
			"convictions": {"violence_thoughts": 0, "deceptive_acts": 0, "compassionate_acts": 0, "duty_above_all": 0},
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
		{
			"talk_to_guard": {"status": "available", "approach_taken": "", "objectives_completed": []},
			"join_rebels": {"status": "available", "approach_taken": "", "objectives_completed": []}
		},
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
	# Emit initial state
	call_deferred("emit_signal", "state_changed", _state.duplicate(true))


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_F5:
			SaveSystem.save_state(snapshot_for_save())
			get_viewport().set_input_as_handled()
		elif event.keycode == KEY_F9:
			var loaded_state = SaveSystem.load_state()
			if not loaded_state.is_empty():
				restore_from_save(loaded_state)
				# Reload current scene to ensure nodes (like QuestTriggers) match the new state
				get_tree().reload_current_scene()
			get_viewport().set_input_as_handled()


func reset() -> void:
	_initialize_state()


## Creates a snapshot of the current state including Dialogic's internal state.
## This should be used instead of accessing `state` directly when saving.
func snapshot_for_save() -> Dictionary:
	var s = state  # Get deep copy via property getter

	# Ensure dialogic subtree exists for save compatibility
	if not s.has("dialogic") or typeof(s["dialogic"]) != TYPE_DICTIONARY:
		s["dialogic"] = {}

	# Snapshot Dialogic's full state (variables, timeline position, history, etc.)
	if Dialogic:
		var dialogic_state: Dictionary = Dialogic.get_full_state()
		s["dialogic"]["engine_state"] = dialogic_state

	return s


## Restores state from save file, including Dialogic's internal state.
## This should be used instead of directly assigning to `_state` when loading.
func restore_from_save(saved_state: Dictionary) -> void:
	# Replace internal state
	_state = saved_state.duplicate(true)

	# Restore Dialogic full state if present
	if _state.has("dialogic") and typeof(_state["dialogic"]) == TYPE_DICTIONARY:
		var dialogic_data = _state["dialogic"]

		if (
			dialogic_data.has("engine_state")
			and typeof(dialogic_data["engine_state"]) == TYPE_DICTIONARY
		):
			if Dialogic and Dialogic.has_method("load_full_state"):
				Dialogic.load_full_state(dialogic_data["engine_state"])

	# Emit state change
	state_changed.emit(_state.duplicate(true))


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
