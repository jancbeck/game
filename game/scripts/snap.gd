## Saves one frame to shots/snap.png after a second and quits (debugging aid).
##   Godot --path game -- --snap
extends Node

func _ready() -> void:
	await get_tree().create_timer(1.5).timeout
	await RenderingServer.frame_post_draw
	var vp: RID = get_parent().view.sv.get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(vp, true)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	await RenderingServer.frame_post_draw
	var gpu := 0.0
	var t0 := Time.get_ticks_usec()
	for i in 20:
		await RenderingServer.frame_post_draw
		gpu += RenderingServer.viewport_get_measured_render_time_gpu(vp)
	print("snap: %.1f ms per frame, world GPU %.1f ms" % [(Time.get_ticks_usec() - t0) / 20000.0, gpu / 20.0])
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://shots"))
	get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path("res://shots/snap.png"))
	var m := get_parent()
	for c in m.crows.crows:
		print("crow %s at frame px %s" % [c.name, m.screen_of(c.global_position)])
	get_tree().quit()
