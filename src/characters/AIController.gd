extends Node

## Basic AI controller for opponent fighter
## Uses distance-based state machine: idle → approach → attack → retreat

enum State { IDLE, APPROACH, ATTACK, RETREAT, BLOCK }

@export var difficulty: float = 1.0  # Multiplier for reaction times and aggression
@export var attack_range: float = 2.5
@export var retreat_range: float = 1.5
@export var idle_duration: float = 1.0
@export var block_chance: float = 0.3

var current_state: State = State.IDLE
var state_timer: float = 0.0
var fighter: Node3D = null
var target: Node3D = null


func _ready() -> void:
	# Wait one frame to ensure Fighter's _ready() has completed
	await get_tree().process_frame

	# When attached to Fighter instance in scene, this node's parent IS the fighter
	fighter = get_parent()

	# Verify it's a CharacterBody3D
	if not fighter or not (fighter is CharacterBody3D):
		push_error("AIController must be child of Fighter CharacterBody3D node")
		return

	fighter.is_ai_controlled = true


func _physics_process(delta: float) -> void:
	if not fighter or not target:
		_find_target()
		return

	state_timer -= delta

	match current_state:
		State.IDLE:
			_state_idle(delta)
		State.APPROACH:
			_state_approach(delta)
		State.ATTACK:
			_state_attack(delta)
		State.RETREAT:
			_state_retreat(delta)
		State.BLOCK:
			_state_block(delta)


func _find_target() -> void:
	var fighters := get_tree().get_nodes_in_group("fighters")
	for f in fighters:
		if f != fighter:
			target = f
			break


func _state_idle(_delta: float) -> void:
	if state_timer <= 0.0:
		var distance: float = fighter.global_position.distance_to(target.global_position)

		if distance > attack_range:
			_change_state(State.APPROACH)
		elif randf() > 0.5:
			_change_state(State.ATTACK)
		else:
			state_timer = idle_duration / difficulty


func _state_approach(delta: float) -> void:
	var distance: float = fighter.global_position.distance_to(target.global_position)

	if distance <= attack_range:
		_change_state(State.ATTACK)
	else:
		fighter.move_toward_position(target.global_position, delta)


func _state_attack(_delta: float) -> void:
	if state_timer <= 0.0:
		var distance: float = fighter.global_position.distance_to(target.global_position)

		if distance <= attack_range:
			# Randomly choose attack type
			if randf() > 0.6:
				fighter.ai_attack_heavy()
			else:
				fighter.ai_attack_light()

			state_timer = randf_range(0.8, 1.5) / difficulty
		else:
			_change_state(State.APPROACH)

		# Sometimes retreat after attack
		if randf() < 0.3:
			_change_state(State.RETREAT)


func _state_retreat(delta: float) -> void:
	var distance: float = fighter.global_position.distance_to(target.global_position)

	if state_timer <= 0.0 or distance > attack_range + 2.0:
		_change_state(State.IDLE)
	else:
		# Move away from target
		var away_direction := (fighter.global_position - target.global_position).normalized()
		away_direction.y = 0.0
		fighter.move_toward_position(fighter.global_position + away_direction * 3.0, delta)


func _state_block(_delta: float) -> void:
	fighter.ai_block(true)

	if state_timer <= 0.0:
		fighter.ai_block(false)
		_change_state(State.IDLE)


func _change_state(new_state: State) -> void:
	current_state = new_state

	match new_state:
		State.IDLE:
			state_timer = idle_duration / difficulty
		State.APPROACH:
			state_timer = 5.0  # Max approach time
		State.ATTACK:
			state_timer = 0.5 / difficulty
		State.RETREAT:
			state_timer = randf_range(0.5, 1.0)
		State.BLOCK:
			state_timer = randf_range(0.5, 1.5)
