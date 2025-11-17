extends CharacterBody3D

## Fighter character with health, movement, and combat
## Uses AnimationTree with state machine for animation control

const GRAVITY: float = 20.0

@export var max_hp: int = 100
@export var move_speed: float = 5.0
@export var turn_speed: float = 10.0
@export var light_attack_damage: int = 10
@export var heavy_attack_damage: int = 20
@export var is_ai_controlled: bool = false

var hp: int
var is_blocking: bool = false
var is_attacking: bool = false
var opponent: Node3D = null

@onready var animation_tree: AnimationTree = $AnimationTree
@onready
var animation_state: AnimationNodeStateMachinePlayback = animation_tree.get("parameters/playback")


func _ready() -> void:
	add_to_group("fighters")
	hp = max_hp

	# Initialize AnimationTree
	if animation_tree:
		animation_tree.active = true
		await get_tree().process_frame
		if animation_state:
			animation_state.travel("idle_standing")


func _physics_process(delta: float) -> void:
	# Apply gravity
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	else:
		velocity.y = 0.0

	if is_ai_controlled:
		move_and_slide()
		return  # AI controller handles movement/combat

	_handle_movement_input(delta)
	_handle_combat_input()

	move_and_slide()


func _handle_movement_input(_delta: float) -> void:
	var input_dir := 0.0

	if Input.is_action_pressed("move_left"):
		input_dir -= 1.0
	if Input.is_action_pressed("move_right"):
		input_dir += 1.0

	if abs(input_dir) > 0.1:
		velocity.x = input_dir * move_speed
		velocity.z = 0.0

		# Always face opponent if available, otherwise face right
		if opponent:
			var direction: float = sign(opponent.global_position.x - global_position.x)
			rotation.y = 0.0 if direction > 0 else PI
		else:
			rotation.y = 0.0

		_set_animation_state("walk_forward")
	else:
		velocity.x = move_toward(velocity.x, 0, move_speed)
		velocity.z = 0.0

		if not is_attacking and not is_blocking:
			_set_animation_state("idle_standing")


func _handle_combat_input() -> void:
	# Block
	if Input.is_action_pressed("block") and not is_attacking:
		is_blocking = true
		_set_animation_state("block_idle")
	elif Input.is_action_just_released("block"):
		is_blocking = false
		_set_animation_state("idle_standing")

	# Attacks (can't attack while blocking)
	if is_blocking or is_attacking:
		return

	if Input.is_action_just_pressed("attack_light"):
		_perform_attack("attack_combo", light_attack_damage)
	elif Input.is_action_just_pressed("attack_heavy"):
		_perform_attack("kick1", heavy_attack_damage)
	elif Input.is_action_just_pressed("jump"):
		_perform_attack("jump_short", 0)  # Jump attack placeholder


func _perform_attack(attack_anim: String, damage: int) -> void:
	is_attacking = true
	_set_animation_state(attack_anim)

	# Deal damage if opponent is in range
	if opponent and CombatManager.is_in_attack_range(self, opponent, 2.5):
		if damage > 0:
			await get_tree().create_timer(0.3).timeout  # Attack delay
			if opponent and not opponent.is_blocking:
				CombatManager.apply_damage(self, opponent, damage)

	# Reset attack state after animation
	await get_tree().create_timer(0.8).timeout
	is_attacking = false
	_set_animation_state("idle_standing")


func _set_animation_state(state_name: String) -> void:
	if not animation_state:
		print("WARNING: animation_state is null")
		return
	if not animation_tree:
		print("WARNING: animation_tree is null")
		return
	if not animation_tree.active:
		print("WARNING: animation_tree not active")
		return
	animation_state.travel(state_name)


func take_damage(amount: int) -> void:
	if is_blocking:
		amount = int(amount * 0.3)  # Block reduces damage by 70%

	hp -= amount
	hp = max(hp, 0)

	if hp <= 0:
		_die()
	else:
		# Play hit reaction
		is_attacking = false
		is_blocking = false
		_set_animation_state("react_gut")
		await get_tree().create_timer(0.5).timeout
		_set_animation_state("idle_standing")


func is_defeated() -> bool:
	return hp <= 0


func _die() -> void:
	_set_animation_state("react_gut")  # Death animation placeholder
	set_physics_process(false)
	# TODO: Add proper death sequence


## AI/External control methods
func move_toward_position(target_pos: Vector3, _delta: float) -> void:
	var direction_x := target_pos.x - global_position.x

	if abs(direction_x) > 0.5:
		velocity.x = sign(direction_x) * move_speed
		velocity.z = 0.0

		# Face opponent
		rotation.y = 0.0 if direction_x > 0 else PI
		_set_animation_state("walk_forward")
	else:
		velocity.x = 0.0
		velocity.z = 0.0
		_set_animation_state("idle_standing")


func ai_attack_light() -> void:
	if not is_attacking and not is_blocking:
		_perform_attack("attack_combo", light_attack_damage)


func ai_attack_heavy() -> void:
	if not is_attacking and not is_blocking:
		_perform_attack("kick1", heavy_attack_damage)


func ai_block(enabled: bool) -> void:
	if enabled and not is_attacking:
		is_blocking = true
		_set_animation_state("block_idle")
	else:
		is_blocking = false
		if not is_attacking:
			_set_animation_state("idle_standing")
