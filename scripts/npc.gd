extends StaticBody2D

## NPC that can be interacted with for dialogue

@export var npc_name: String = "NPC"
@export var dialogue_start_node: String = "start"

var dialogue_system: DialogueSystem
var player_in_range: bool = false


func _ready():
	dialogue_system = DialogueSystem.new()
	add_child(dialogue_system)

	# Connect to area for interaction detection
	var area = get_node_or_null("InteractionArea")
	if area:
		area.body_entered.connect(_on_body_entered)
		area.body_exited.connect(_on_body_exited)


func _on_body_entered(body):
	if body.is_in_group("player"):
		player_in_range = true
		body.set_can_interact(true, self)


func _on_body_exited(body):
	if body.is_in_group("player"):
		player_in_range = false
		body.set_can_interact(false)


func interact(player):
	if player.has_method("start_dialogue"):
		player.start_dialogue()
		dialogue_system.start_dialogue(dialogue_start_node, player.stats)

		# Signal UI to show dialogue
		get_tree().call_group("ui", "show_dialogue", dialogue_system)
