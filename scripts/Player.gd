extends CharacterBody2D

@export var move_speed: float = 250.0
@export var bullet_scene: PackedScene = preload("res://scenes/Bullet.tscn")
@export var max_hp: int = 100

var fire_cooldown: float
var can_fire := true
var hp: int
var tex: Texture2D
var cell_w: int
var cell_h: int


func _ready() -> void:
	add_to_group("player")
	hp = max_hp

	# Use persistent fire cooldown from autoload
	fire_cooldown = PlayerState.fire_cooldown

	# Load 3x3 directional sprite sheet
	tex = load("res://art/player_8dir.png")
	$"Sprite".texture = tex
	$"Sprite".centered = true
	$"Sprite".region_enabled = true

	# Each sprite cell is 1024/3 = 341px
	cell_w = int(tex.get_width() / 3.0)
	cell_h = int(tex.get_height() / 3.0)
	_set_dir_frame(7)  # Start facing south

	$"FireCD".wait_time = fire_cooldown
	$"FireCD".timeout.connect(_on_FireCD_timeout)

	$"HitFlash".timeout.connect(_on_hit_flash_timeout)


func _physics_process(_delta: float) -> void:
	var dir := (
		Vector2(
			int(Input.is_action_pressed("move_right")) - int(Input.is_action_pressed("move_left")),
			int(Input.is_action_pressed("move_down")) - int(Input.is_action_pressed("move_up"))
		)
		. normalized()
	)
	velocity = dir * move_speed
	move_and_slide()

	# Update sprite direction to face mouse cursor
	var mouse_offset := get_global_mouse_position() - global_position
	if mouse_offset.length() > 10.0:  # Deadzone prevents flicker at origin
		var ang := mouse_offset.angle()
		var sector := int(floor(fmod(ang + PI / 8.0, TAU) / (PI / 4.0)))  # 0-7 octants
		# Map octants (E,NE,N,NW,W,SW,S,SE) to 3x3 sprite grid indices
		var map := [3, 0, 1, 2, 5, 8, 7, 6]
		_set_dir_frame(map[sector])

	if Input.is_action_pressed("shoot") and can_fire:
		_shoot()

	Utils.ysort_by_y(self)


func _set_dir_frame(idx: int) -> void:
	# Map 3x3 grid index to sprite sheet region
	var cx := idx % 3
	var cy := idx / 3
	$"Sprite".region_rect = Rect2(cx * cell_w, cy * cell_h, cell_w, cell_h)

	# Scale to consistent 128px height regardless of source size
	var desired_h := 128.0
	var s := desired_h / float(cell_h)
	$"Sprite".scale = Vector2(s, s)


func _shoot() -> void:
	can_fire = false
	$"FireCD".start()
	var b := bullet_scene.instantiate()
	var aim := (get_global_mouse_position() - global_position).normalized()
	get_tree().current_scene.add_child(b)
	b.global_position = global_position + aim * 32.0
	b.dir = aim

	# Play random shooting sound effect
	var sfx_choice := randi() % 3
	match sfx_choice:
		0:
			$"ShootSFX1".play()
		1:
			$"ShootSFX2".play()
		2:
			$"ShootSFX3".play()


func _on_FireCD_timeout() -> void:
	can_fire = true


func take_damage(amount: int) -> void:
	hp -= amount
	hp = max(hp, 0)

	# Red flash for damage feedback
	$"Sprite".modulate = Color(0.6, 0.1, 0.1, 1.0)
	$"HitFlash".start()

	if hp <= 0:
		_die()


func _on_hit_flash_timeout() -> void:
	$"Sprite".modulate = Color(1, 1, 1, 1)


func _die() -> void:
	# Reset all boons and reload room
	PlayerState.reset()
	SceneTransition.fade_to_black_and_reload(0.8)
