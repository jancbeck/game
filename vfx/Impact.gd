extends Sprite2D

var cols := 3
var rows := 2
var current_frame := 0
var total := cols * rows
var frame_time := 0.04
var cell := Vector2i.ZERO


func _ready() -> void:
	centered = true

	if ResourceLoader.exists("res://vfx/impact_small.png"):
		texture = load("res://vfx/impact_small.png")
		region_enabled = true
		var w := texture.get_width() / cols
		var h := texture.get_height() / rows
		cell = Vector2i(w, h)

		# Scale down from 500x500 grid (each cell ~166x250) to bigger size (~80px for 2.5x effect)
		var desired_size := 80.0
		var cell_size := float(max(cell.x, cell.y))
		var scale_factor: float = desired_size / cell_size
		scale = Vector2(scale_factor, scale_factor)

		_set_frame(0)
		_play()
	else:
		# Fallback: quick white circle flash
		var img := Image.create(32, 32, false, Image.FORMAT_RGBA8)
		img.fill(Color(0, 0, 0, 0))
		for y in range(32):
			for x in range(32):
				var d: float = Vector2(x - 15.5, y - 15.5).length()
				if d <= 14.0:
					var t: float = clamp(1.0 - d / 14.0, 0.0, 1.0)
					img.set_pixel(x, y, Color(1, 1, 1, t))
		texture = ImageTexture.create_from_image(img)
		region_enabled = false
		modulate = Color(1, 1, 1, 1)
		await get_tree().create_timer(0.08).timeout
		queue_free()


func _play() -> void:
	for i in total:
		_set_frame(i)
		await get_tree().create_timer(frame_time).timeout
	queue_free()


func _set_frame(i: int) -> void:
	current_frame = i % total
	var cx := current_frame % cols
	var cy := current_frame / cols
	region_rect = Rect2(cx * cell.x, cy * cell.y, cell.x, cell.y)
