class_name PlayerSystem
extends RefCounted


## Pure reducer for player movement.
## Returns a new state with updated player position.
static func move(state: Dictionary, direction: Vector3, delta: float = 1.0) -> Dictionary:
	var new_state: Dictionary = state.duplicate(true)
	var speed: float = 5.0

	var current_pos: Vector3 = new_state["player"]["position"]
	var displacement: Vector3 = direction.normalized() * speed * delta

	new_state["player"]["position"] = current_pos + displacement

	return new_state
