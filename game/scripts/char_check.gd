## Check run for the figures: the player and Marl idle, Marl talking, and the player walking, at
## zoom 1 and zoom 2. Saves crops around the figures (3x, nearest) and the full frames.
##   Godot --path game --resolution 2560x1440 --audio-driver Dummy -- --no-intro --char-check
## Writes game/shots/chars/*.png.
extends Node

const CROP_PX := 150      # half size of a crop in screen px, before the 3x upscale

var main: Node
var out_dir: String


func _ready() -> void:
	main = get_parent()
	out_dir = ProjectSettings.globalize_path("res://shots/chars")
	DirAccess.make_dir_recursive_absolute(out_dir)
	_run.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw


## Saves the full frame and, around `point`, a crop scaled 3x.
func _shot(name: String, point: Vector3, crop := true) -> void:
	await _frames(2)
	var img := get_viewport().get_texture().get_image()
	var s: Vector2 = main.screen_of(point)
	var scale := float(img.get_width()) / float(get_viewport().get_visible_rect().size.x)
	if crop:
		var r := Rect2i(Vector2i((s * scale - Vector2(CROP_PX, CROP_PX * 1.4)).round()), Vector2i(CROP_PX * 2, int(CROP_PX * 2.4)))
		var c := img.get_region(r.intersection(Rect2i(Vector2i.ZERO, img.get_size())))
		c.resize(c.get_width() * 3, c.get_height() * 3, Image.INTERPOLATE_NEAREST)
		c.save_png(out_dir.path_join(name + "_crop.png"))
	else:
		img.save_png(out_dir.path_join(name + ".png"))
	print("shot ", name, " at ", s)


func _focus(point: Vector3, zoom: float) -> void:
	main.rig.set_view(main.rig.frame_px_of(point), zoom)


func _run() -> void:
	await get_tree().create_timer(2.5).timeout
	var player = main.player
	var marl = main.npcs[0].figure if not main.npcs.is_empty() else null
	var marl_pos: Vector3 = marl.global_position if marl else Vector3(1.6, 0, -1.3)
	player.global_position = main.nav.nav_point(marl_pos + Vector3(-1.6, 0.0, 0.5))
	player.face(marl_pos)
	var mid: Vector3 = (player.global_position + marl_pos) * 0.5 + Vector3(0, 0.9, 0)
	for z in [1.0, 2.0]:
		_focus(mid, z)
		await get_tree().create_timer(0.8).timeout
		await _shot("idle_zoom%d" % int(z), mid)
		if z == 1.0:
			await _shot("idle_zoom1_full", mid, false)
	# Marl talking
	if marl:
		marl.set_talking(true)
		await get_tree().create_timer(1.5).timeout
		_focus(mid, 2.0)
		await _shot("talk_zoom2", marl_pos + Vector3(0, 0.9, 0))
		marl.set_talking(false)
	# the player walks away from Marl; frames across a few strides
	var start: Vector3 = player.global_position
	var goal: Vector3 = main.nav.nav_point(start + Vector3(-4.0, 0.0, 3.0))
	player.walk_to(goal)
	await get_tree().create_timer(0.9).timeout
	for z in [1.0, 2.0]:
		for k in 6:
			var p: Vector3 = player.global_position + Vector3(0, 0.9, 0)
			_focus(p, z)
			await _shot("walk_zoom%d_%d" % [int(z), k], p)
			await get_tree().create_timer(0.14).timeout
	print("char-check done")
	get_tree().quit()
