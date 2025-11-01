class_name NPCPlacement
extends Resource

## Describes an NPC instance in a location
## Self-contained: all info about this NPC's placement

@export var npc_id: String  ## Must exist in EntityRegistry.NPCS
@export var position: Vector2  ## Where to spawn in scene
## Optional: GDScript expression (e.g., "GameState.flags.met_kim")
@export var spawn_condition: String = ""
@export var dialogue_override: String = ""  ## Optional: Override NPC's default dialogue


func _to_string() -> String:
	return (
		"NPCPlacement[npc=%s, pos=(%d,%d), condition=%s]"
		% [npc_id, position.x, position.y, spawn_condition if spawn_condition else "always"]
	)


## Check if this NPC should spawn
func should_spawn() -> bool:
	if spawn_condition.is_empty():
		return true

	# Evaluate spawn condition
	var expression := Expression.new()
	var error := expression.parse(spawn_condition)
	if error != OK:
		push_error("Invalid spawn condition: %s" % spawn_condition)
		return false

	var result = expression.execute([], null)
	return result if result is bool else false
