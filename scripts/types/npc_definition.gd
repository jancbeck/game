class_name NPCDefinition
extends Resource

## Self-documenting NPC definition
## All NPC properties in one place - no external docs needed

@export var npc_id: String  ## Unique identifier (e.g., "kim_kitsuragi")
@export var display_name: String  ## Name shown in game (e.g., "Kim Kitsuragi")
@export var sprite: Texture2D  ## Character sprite
@export var dialogue_tree_id: String  ## ID of dialogue tree (must exist in DialogueRegistry)
@export var description: String  ## Brief description for agents to understand context
@export_multiline var backstory: String  ## Optional: deeper context for agents

## Additional properties
@export var is_hostile: bool = false
@export var can_trade: bool = false
@export var initial_position: Vector2 = Vector2.ZERO  ## Default spawn position


func _to_string() -> String:
	return "NPC[id=%s, name=%s, dialogue=%s]" % [npc_id, display_name, dialogue_tree_id]
