## Saves frames of the background alone, to compare the raw EXR data with the release data
## (scripts/release.py compare runs it twice):
##
##   Godot --path game --resolution 2560x1440 -- --release-shot=<dir> [--raw] [--tiles=forge,well]
##
## The picture is frozen: every light group at intensity 1, no rain, flipbooks, crows, people or
## real-time lights. It writes wide.png (zoom 0.5), main.png (zoom 1) and tile_<id>.png (zoom 2 on
## the tile), the screen as the player sees it, and prints the frame time (wall clock with vsync
## off, and the GPU time of the world view), video and texture memory of the main view and of
## each tile.
extends Node

const DEFAULT_TILES := ["forge", "well", "gate"]

var main: Node
var dir := ""
var tiles: Array = DEFAULT_TILES


func _ready() -> void:
	main = get_parent()
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--release-shot="):
			dir = arg.substr(15)
		elif arg.begins_with("--tiles="):
			tiles = arg.substr(8).split(",", false)
	DirAccess.make_dir_recursive_absolute(dir)
	_run.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw


func _save(name: String) -> void:
	await _frames(4)
	get_viewport().get_texture().get_image().save_png(dir.path_join(name + ".png"))
	print("saved %s" % name)


func _run() -> void:
	main.compositor.frozen = true
	main.paused_clock = true
	main.set_rain(false)
	for part in [main.rain, main.flipbooks, main.crows, main.lights, main.player]:
		part.visible = false
	for n in main.npcs:
		n.visible = false
	var rig = main.rig
	rig.set_view(rig.frame * 0.5, 0.5)
	await _save("wide")
	rig.set_view(rig.frame * 0.5, 1.0)
	await _save("main")
	await _timing("main")
	for id in tiles:
		main.compositor.request_tile(id)
		while not main.compositor.tile_ready(id):
			await get_tree().process_frame
		rig.set_view(main.compositor.tile_rect(id).get_center(), 2.0)
		await _save("tile_" + id)
		await _timing("tile " + id)
	get_tree().quit()


## Frame time of the current view over 120 frames with vsync off.
func _timing(label: String) -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	await _frames(20)
	var vp: RID = main.view.sv.get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(vp, true)
	var gpu := 0.0
	var t0 := Time.get_ticks_usec()
	for i in 120:
		await RenderingServer.frame_post_draw
		gpu += RenderingServer.viewport_get_measured_render_time_gpu(vp)
	print("frame %s: %.2f ms per frame, world GPU %.2f ms, video memory %.0f MB, texture memory %.0f MB" % [
		label, (Time.get_ticks_usec() - t0) / 120000.0, gpu / 120.0,
		Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0,
		Performance.get_monitor(Performance.RENDER_TEXTURE_MEM_USED) / 1048576.0])
