extends Node3D
## Fixed-angle isometric camera that smoothly follows a target.
## Yaw 45° / pitch -50° is set in the scene; this script only translates.

@export var target_path: NodePath
@export var follow_speed := 6.0
@export var yaw_degrees := 45.0
@export var pitch_degrees := -50.0
@export var distance := 16.0

var _target: Node3D


func _ready() -> void:
	rotation_degrees.y = yaw_degrees
	var camera: Camera3D = $Camera3D
	camera.rotation_degrees.x = pitch_degrees
	# Pull the camera back along its own view axis so it looks at the rig.
	camera.position = camera.basis.z * distance
	_target = get_node_or_null(target_path)
	if _target:
		global_position = _target.global_position


func _process(delta: float) -> void:
	if _target:
		global_position = global_position.lerp(_target.global_position, follow_speed * delta)
