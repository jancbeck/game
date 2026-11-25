## Motion clips for checking under Movie Maker (fixed 24 fps, so drops and the camera move by
## exactly 1/24 s per frame):
##
##   Godot --path game --resolution 2560x1440 --write-movie shots/clip/rain1/f.png --fixed-fps 24 -- --clip=rain1
##
## --clip=rain1      4 s of rain at zoom 1
## --clip=rain2      4 s of rain at zoom 2 on the gallows tile
## --clip=intro      the intro, zoom 0.5 to 1
## --clip=interact   click the gallows beam: walk, zoom to 2, close the dialogue, zoom back
extends Node

const SceneData := preload("res://scripts/scene_data.gd")

var main: Node
var mode := ""


func _ready() -> void:
	main = get_parent()
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--clip="):
			mode = arg.substr(7)
	_run.call_deferred()


func _seconds(s: float) -> void:
	await get_tree().create_timer(s).timeout


func _run() -> void:
	while not main.nav.ready_map():
		await get_tree().process_frame
	match mode:
		"rain1":
			main.rig.set_view(main.rig.frame * 0.5, 1.0)
			await _seconds(4.0)
		"rain2":
			main.compositor.request_tile("gallows")
			while not main.compositor.tile_ready("gallows"):
				await get_tree().process_frame
			main.rig.set_view(main.compositor.tile_rect("gallows").get_center(), 2.0)
			await _seconds(4.0)
		"intro":
			await _seconds(8.0)
		"interact":
			main.rig.set_view(main.rig.frame * 0.5, 1.0)
			main.player.global_position = main.nav.nav_point(Vector3(1.0, 0.0, 2.6))
			await _seconds(0.5)
			main.click(main.screen_of(Vector3(3.9, 3.0, 0.5)))
			while not main.ui.is_open():
				await get_tree().process_frame
			await _seconds(3.5)
			main.ui.close()
			await _seconds(3.0)
	get_tree().quit()
