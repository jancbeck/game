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


## Modifies a flexibility stat by the given amount.
## Clamps the result between 0 and 10.
## Returns a new state.
static func modify_flexibility(state: Dictionary, stat_name: String, amount: int) -> Dictionary:
	var new_state = state.duplicate(true)

	if not new_state["player"]["flexibility"].has(stat_name):
		push_warning("Attempted to modify non-existent flexibility stat: " + stat_name)
		return state

	new_state["player"]["flexibility"][stat_name] += amount
	new_state["player"]["flexibility"][stat_name] = clampi(
		new_state["player"]["flexibility"][stat_name], 0, 10
	)

	return new_state


## Modifies a conviction stat by the given amount.
## Clamps the result to a minimum of 0.
## Returns a new state.
static func modify_conviction(
	state: Dictionary, conviction_name: String, amount: int
) -> Dictionary:
	var new_state = state.duplicate(true)

	if not new_state["player"]["convictions"].has(conviction_name):
		push_warning("Attempted to modify non-existent conviction stat: " + conviction_name)
		return state

	new_state["player"]["convictions"][conviction_name] += amount
	# Convictions can grow, but probably shouldn't be negative
	new_state["player"]["convictions"][conviction_name] = max(
		0, new_state["player"]["convictions"][conviction_name]
	)

	return new_state
