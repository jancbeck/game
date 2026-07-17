class_name Player
extends CharacterBody3D
## Top-down player controller. Movement is relative to the isometric camera:
## screen-up moves away from the camera, screen-right moves right.

const SPEED := 5.0
const TURN_SPEED := 12.0

var input_enabled := true

@onready var body: Node3D = $Body

var _walk_phase := 0.0


func _physics_process(delta: float) -> void:
	var input_dir := Vector2.ZERO
	if input_enabled:
		input_dir = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	# Camera yaw is fixed at 45°; rotate input to match what the player sees.
	var direction := (Vector3(input_dir.x, 0, input_dir.y)).rotated(Vector3.UP, deg_to_rad(-45.0))
	if direction.length() > 0.01:
		velocity.x = direction.x * SPEED
		velocity.z = direction.z * SPEED
		var target_yaw := atan2(-direction.x, -direction.z)
		body.rotation.y = lerp_angle(body.rotation.y, target_yaw, TURN_SPEED * delta)
		_animate_walk(delta)
	else:
		velocity.x = move_toward(velocity.x, 0, SPEED)
		velocity.z = move_toward(velocity.z, 0, SPEED)
		_animate_idle(delta)
	if not is_on_floor():
		velocity.y -= 20.0 * delta
	move_and_slide()


func _animate_walk(delta: float) -> void:
	# Procedural bob + lean instead of skeletal animation.
	_walk_phase += delta * 10.0
	body.position.y = absf(sin(_walk_phase)) * 0.08
	body.rotation.x = sin(_walk_phase * 0.5) * 0.03


func _animate_idle(delta: float) -> void:
	_walk_phase = 0.0
	body.position.y = lerpf(body.position.y, 0.0, 8.0 * delta)
	body.rotation.x = lerpf(body.rotation.x, 0.0, 8.0 * delta)
