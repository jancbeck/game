extends Node2D

@export var enemy_scene: PackedScene = preload("res://scenes/Enemy.tscn")
@export var player_scene: PackedScene = preload("res://scenes/Player.tscn")
@export var boon_scene: PackedScene = preload("res://scenes/Boon.tscn")

@export var enemy_count: int = 3

var player: Node2D
var playable_area: Rect2
var boon_spawned := false


func _ready() -> void:
	$"Background".texture = load("res://art/room_base.png")
	$"Background".centered = false

	# Scale 1024x1024 room to fit 720p viewport without cropping
	var viewport_size := Vector2(1280, 720)
	var texture_size := Vector2(
		$"Background".texture.get_width(), $"Background".texture.get_height()
	)
	var scale_x := viewport_size.x / texture_size.x
	var scale_y := viewport_size.y / texture_size.y
	var bg_scale: float = min(scale_x, scale_y)  # Fit entire room in view
	$"Background".scale = Vector2(bg_scale, bg_scale)

	# Center background with letterboxing
	var scaled_size: Vector2 = texture_size * bg_scale
	$"Background".position = (viewport_size - scaled_size) / 2.0

	var room_w: int = int(texture_size.x * bg_scale)
	var room_h: int = int(texture_size.y * bg_scale)
	var offset: Vector2 = $"Background".position
	var m := int(112 * bg_scale)  # Wall thickness scaled
	var door_w := int(256 * bg_scale)  # Exit gap width scaled
	var inner := Rect2(offset.x + m, offset.y + m, room_w - 2 * m, room_h - 2 * m)

	playable_area = inner

	# Position decorative bottom wall overlay
	var bottom_wall_tex := load("res://art/room_bottom.png") as Texture2D
	if bottom_wall_tex:
		var bottom_wall_height: int = bottom_wall_tex.get_height()
		var bottom_wall_width: int = bottom_wall_tex.get_width()
		var scaled_wall_width: float = bottom_wall_width * bg_scale
		var bottom_pos := Vector2(
			offset.x, offset.y + scaled_size.y - (bottom_wall_height * bg_scale)
		)
		$"BottomWall".texture = bottom_wall_tex
		$"BottomWall".centered = false
		$"BottomWall".scale = Vector2(bg_scale, bg_scale)
		$"BottomWall".position = bottom_pos
		$"BottomWall".z_index = 1000  # Above player for depth effect

	# Create collision walls around room edges
	_add_rect($"Walls", Rect2(inner.position.x, inner.position.y - m, inner.size.x, m))
	_add_rect($"Walls", Rect2(inner.position.x - m, inner.position.y, m, inner.size.y))
	_add_rect($"Walls", Rect2(inner.position.x + inner.size.x, inner.position.y, m, inner.size.y))

	# Bottom walls split for exit gap in center
	var gap_x := inner.position.x + (inner.size.x - door_w) * 0.5
	_add_rect(
		$"Walls",
		Rect2(inner.position.x, inner.position.y + inner.size.y, gap_x - inner.position.x, m)
	)
	_add_rect(
		$"Walls",
		Rect2(
			gap_x + door_w,
			inner.position.y + inner.size.y,
			inner.position.x + inner.size.x - (gap_x + door_w),
			m
		)
	)

	# Exit trigger positioned in bottom gap
	$"Exit/CollisionShape2D".shape = RectangleShape2D.new()
	($"Exit/CollisionShape2D".shape as RectangleShape2D).size = Vector2(door_w, m * 0.6)
	$"Exit".position = Vector2(gap_x + door_w * 0.5, inner.position.y + inner.size.y + m * 0.2)
	$"Exit".monitoring = true
	$"Exit".body_entered.connect(_on_exit_body_entered)

	# Generate enemy spawn points if not manually placed (top half only)
	var spawn_offset := 128 * bg_scale
	if $"Spawns".get_child_count() == 0:
		var center_y := inner.get_center().y
		var pts := [
			Vector2(inner.position.x + spawn_offset, inner.position.y + spawn_offset),
			Vector2(
				inner.position.x + inner.size.x - spawn_offset, inner.position.y + spawn_offset
			),
			Vector2(inner.get_center().x, center_y - 80 * bg_scale),
		]
		for p in pts:
			var mk := Marker2D.new()
			mk.position = p
			$"Spawns".add_child(mk)

	# Spawn player at bottom center of room
	player = player_scene.instantiate()
	add_child(player)
	player.global_position = Vector2(
		inner.get_center().x, inner.position.y + inner.size.y - spawn_offset
	)

	# Spawn enemies at marker positions (cycling if more enemies than markers)
	var spawns := $"Spawns".get_children()
	for i in enemy_count:
		var e := enemy_scene.instantiate()
		add_child(e)
		var mki := spawns[i % spawns.size()] as Marker2D
		e.global_position = mki.global_position

	$"WaveCheck".timeout.connect(_on_wave_check)

	# Start room music
	MusicManager.start_room_music()


func _add_rect(parent: Node, r: Rect2) -> void:
	var cs := CollisionShape2D.new()
	var shape := RectangleShape2D.new()
	shape.size = Vector2(max(r.size.x, 1.0), max(r.size.y, 1.0))
	cs.shape = shape
	cs.position = r.position + r.size * 0.5
	parent.add_child(cs)


func _on_wave_check() -> void:
	if not get_tree().get_nodes_in_group("enemies").is_empty():
		return

	# Fade back to calm music when all enemies are dead
	MusicManager.trigger_calm()

	# Only spawn boon once per room and only if not at max upgrade
	if not boon_spawned and not PlayerState.is_max_fire_rate():
		_spawn_boon()
		boon_spawned = true


func _spawn_boon() -> void:
	var b := boon_scene.instantiate()
	add_child(b)
	b.global_position = playable_area.get_center() + Vector2(0, -64)


func _on_exit_body_entered(body: Node) -> void:
	if body.is_in_group("player"):
		SceneTransition.fade_to_black_and_reload(0.6)
