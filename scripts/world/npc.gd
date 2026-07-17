class_name Npc
extends Node3D
## A talkable character in the world. When the player is inside the
## interaction area and presses "interact", main.gd starts this NPC's
## dialogue. Idle life comes from procedural sway, not skeletal animation.

signal player_entered(npc: Npc)
signal player_exited(npc: Npc)

@export var npc_name: String = "Stranger"
@export var dialogue_id: String = ""
## Sway phase offset so a crowd of NPCs doesn't move in lockstep.
@export var sway_seed: float = 0.0
@onready var body: Node3D = $Body
@onready var name_label: Label3D = $NameLabel

var _time := 0.0


func _ready() -> void:
	name_label.text = npc_name
	var area: Area3D = $InteractionArea
	area.body_entered.connect(_on_body_entered)
	area.body_exited.connect(_on_body_exited)


func _process(delta: float) -> void:
	_time += delta
	var t := _time + sway_seed
	body.rotation.y = sin(t * 0.4) * 0.15
	body.position.y = sin(t * 1.1) * 0.02


## Turn to face a world position (used when conversation starts).
func face(world_pos: Vector3) -> void:
	var flat := Vector3(world_pos.x, global_position.y, world_pos.z)
	if flat.distance_to(global_position) > 0.1:
		look_at(flat, Vector3.UP)


func _on_body_entered(other: Node3D) -> void:
	if other is Player:
		player_entered.emit(self)


func _on_body_exited(other: Node3D) -> void:
	if other is Player:
		player_exited.emit(self)
