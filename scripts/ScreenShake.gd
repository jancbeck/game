extends Node

# Screen shake manager for camera trauma effects

var trauma: float = 0.0
var trauma_decay: float = 1.5  # How fast trauma decays per second
var max_offset: float = 75.0
var max_rotation: float = 0.15  # Radians


func _ready() -> void:
	# Ensure shake continues during pause (e.g., during hit-stop)
	process_mode = Node.PROCESS_MODE_ALWAYS


func _process(delta: float) -> void:
	if trauma <= 0.0:
		return

	# Find camera each frame in case scene was reloaded
	var camera := get_tree().get_first_node_in_group("camera") as Camera2D
	if not camera:
		return

	# Decay trauma over time
	trauma = max(trauma - trauma_decay * delta, 0.0)

	# Shake amount is squared for smoother feel
	var shake: float = trauma * trauma

	# Random offset and rotation based on shake intensity
	var offset := Vector2(
		randf_range(-max_offset, max_offset) * shake, randf_range(-max_offset, max_offset) * shake
	)
	var rotation: float = randf_range(-max_rotation, max_rotation) * shake

	camera.offset = offset
	camera.rotation = rotation


func add_trauma(amount: float) -> void:
	# Add trauma clamped to 0-1 range
	trauma = min(trauma + amount, 1.0)
