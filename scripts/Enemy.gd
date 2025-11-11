extends CharacterBody2D

@export var max_hp: int = 40
@export var speed: float = 150.0
@export var patrol_speed: float = 75.0
@export var aggro_range: float = 200.0
@export var contact_damage: int = 10
@export var contact_cooldown: float = 1.0

var hp: int
var player: Node2D
var patrol_target: Vector2
var spawn_position: Vector2
var last_position: Vector2
var stuck_timer: float = 0.0
var is_aggroed: bool = false
var can_damage: bool = true


func _ready() -> void:
	add_to_group("enemies")
	hp = max_hp
	$"Sprite".texture = load("res://art/enemy_blob.png")
	$"Sprite".centered = true

	# Scale 1024x1024 blob to 64px
	var desired_size := 64.0
	var texture_size: int = $"Sprite".texture.get_width()
	var scale_factor: float = desired_size / texture_size
	$"Sprite".scale = Vector2(scale_factor, scale_factor)

	player = get_tree().get_first_node_in_group("player")
	call_deferred("_init_patrol")  # Wait for position to be set

	$"HitFlash".timeout.connect(_on_hit_flash_timeout)
	$"ContactDamageCD".wait_time = contact_cooldown
	$"ContactDamageCD".timeout.connect(_on_contact_damage_cd_timeout)


func _init_patrol() -> void:
	spawn_position = global_position
	last_position = global_position
	_pick_new_patrol_target()


func _physics_process(delta: float) -> void:
	if player:
		var dist_to_player: float = global_position.distance_to(player.global_position)

		if is_aggroed or dist_to_player < aggro_range:
			# Once aggroed, always chase at full speed
			if not is_aggroed:
				is_aggroed = true
				MusicManager.trigger_aggro()
			var v := (player.global_position - global_position).normalized() * speed
			velocity = v
			stuck_timer = 0.0
		else:
			# Patrol behavior: wander around spawn point
			if global_position.distance_to(patrol_target) < 20.0:
				_pick_new_patrol_target()

			# Detect if stuck on obstacle and pick new target
			if global_position.distance_to(last_position) < 5.0:
				stuck_timer += delta
				if stuck_timer > 1.5:
					_pick_new_patrol_target()
					stuck_timer = 0.0
			else:
				stuck_timer = 0.0

			last_position = global_position
			var v := (patrol_target - global_position).normalized() * patrol_speed
			velocity = v

		move_and_slide()

		# Deal contact damage to player with cooldown
		for i in get_slide_collision_count():
			var collision := get_slide_collision(i)
			if collision.get_collider().is_in_group("player") and can_damage:
				if "take_damage" in collision.get_collider():
					collision.get_collider().take_damage(contact_damage)
					can_damage = false
					$"ContactDamageCD".start()

	Utils.ysort_by_y(self)


func _pick_new_patrol_target() -> void:
	# Wander in 200px radius around spawn position
	var offset := Vector2(randf_range(-100, 100), randf_range(-100, 100))
	patrol_target = spawn_position + offset


func take_damage(amount: int) -> void:
	hp -= amount
	if not is_aggroed:
		is_aggroed = true
		MusicManager.trigger_aggro()

	# Red flash for damage feedback
	$"Sprite".modulate = Color(0.6, 0.1, 0.1, 1.0)
	$"HitFlash".start()

	_spawn_impact()
	if hp <= 0:
		_die()


func _on_hit_flash_timeout() -> void:
	$"Sprite".modulate = Color(1, 1, 1, 1)


func _on_contact_damage_cd_timeout() -> void:
	can_damage = true


func _spawn_impact() -> void:
	var scene := load("res://scenes/Impact.tscn") as PackedScene
	var fx := scene.instantiate() as Sprite2D
	get_tree().current_scene.add_child(fx)
	fx.global_position = global_position


func _die() -> void:
	remove_from_group("enemies")
	queue_free()
