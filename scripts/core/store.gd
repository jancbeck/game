extends Node
## Immutable game-state store. The single source of truth for all game logic.
##
## State is a plain Dictionary. It can only change via dispatch(reducer),
## where the reducer receives a deep copy and returns the next state.
## The private _state is never handed out directly, so nothing outside
## this node can mutate it in place.

signal state_changed(new_state: Dictionary)

var _state: Dictionary = {}


func _ready() -> void:
	reset()


func reset() -> void:
	_state = initial_state()
	state_changed.emit(get_state())


static func initial_state() -> Dictionary:
	var attributes := {}
	for attr_id: String in ["might", "guile", "lore", "heart"]:
		attributes[attr_id] = {"score": 1, "flexibility": 10}
	return {
		"version": 1,
		"player": {"attributes": attributes},
		"quests": {"active": [], "completed": {}},
		"flags": [],
		"journal": [],
	}


func get_state() -> Dictionary:
	return _state.duplicate(true)


## Apply a reducer: Callable(state: Dictionary, args...) -> Dictionary.
## Extra args are bound after the state copy.
func dispatch(reducer: Callable, args: Array = []) -> void:
	var call_args: Array = [get_state()]
	call_args.append_array(args)
	var next: Variant = reducer.callv(call_args)
	if not next is Dictionary:
		push_error("Reducer %s returned %s, expected Dictionary" % [reducer, typeof(next)])
		return
	if next.hash() == _state.hash():
		return
	_state = next
	state_changed.emit(get_state())


## Replace the whole state (save/load only). Validates the shape first.
func restore(loaded: Dictionary) -> bool:
	if not _is_valid_shape(loaded):
		push_error("Store.restore: rejected malformed state")
		return false
	_state = loaded.duplicate(true)
	state_changed.emit(get_state())
	return true


static func _is_valid_shape(s: Dictionary) -> bool:
	if not (s.has("player") and s.has("quests") and s.has("flags")):
		return false
	var player: Variant = s["player"]
	if not (player is Dictionary and player.has("attributes")):
		return false
	var quests: Variant = s["quests"]
	return quests is Dictionary and quests.has("active") and quests.has("completed")
