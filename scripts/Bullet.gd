extends Area2D

@export var speed: float = 900.0
@export var damage: int = 20
var dir: Vector2 = Vector2.RIGHT


func _ready() -> void:
	monitoring = true
	input_pickable = false
	# Build a small white circle procedurally:
	var img := Image.create(16, 16, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for y in range(16):
		for x in range(16):
			var d: float = Vector2(x - 7.5, y - 7.5).length()
			if d <= 7.0:
				var t: float = clamp(1.0 - ((d - 5.0) / 2.0), 0.0, 1.0)
				img.set_pixel(x, y, Color(1, 0.9, 0.2, 0.8 * t + 0.2))
	var bullet_tex: Texture2D = ImageTexture.create_from_image(img)
	$"Sprite".texture = bullet_tex

	$"Life".timeout.connect(_on_Life_timeout)
	body_entered.connect(_on_Bullet_body_entered)
	area_entered.connect(_on_Bullet_area_entered)


func _physics_process(delta: float) -> void:
	position += dir * speed * delta
	Utils.ysort_by_y(self)


func _on_Life_timeout() -> void:
	queue_free()


func _on_Bullet_body_entered(body: Node) -> void:
	if body.is_in_group("enemies") and body.has_method("take_damage"):
		body.take_damage(damage)
	else:
		# Hit a wall or other body, spawn impact
		_spawn_impact()
	queue_free()


func _on_Bullet_area_entered(_area: Area2D) -> void:
	# Hit something (could be wall area), spawn impact
	_spawn_impact()
	queue_free()


func _spawn_impact() -> void:
	var scene := load("res://scenes/Impact.tscn") as PackedScene
	var fx := scene.instantiate() as Sprite2D
	get_tree().current_scene.add_child(fx)
	fx.global_position = global_position
