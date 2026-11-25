## Scripted check run: measures the view transform against reference.png and the frame time, and
## saves check frames: the three zoom levels with the walk overlay, the hover outline and Tab, the
## click rule on the gallows, well, cart and stair, the interaction zoom, a portal transit, the
## stairs, an exit and a crow in flight.
##
##   Godot --path game --resolution 2560x1440 -- --capture [--checks]
##
## --checks stops after the reference comparisons and the frame times.
##
## Writes game/shots/*.png and prints a report. Needs a window (headless has no renderer).
## Motion clips (rain, intro, interaction zoom) come from clip.gd under Movie Maker.
extends Node

const SceneData := preload("res://scripts/scene_data.gd")

var main: Node
var out_dir: String


func _ready() -> void:
	main = get_parent()
	out_dir = ProjectSettings.globalize_path("res://shots")
	DirAccess.make_dir_recursive_absolute(out_dir)
	_run.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw


func _grab() -> Image:
	await _frames(3)
	return get_viewport().get_texture().get_image()


func _shot(name: String) -> void:
	var img := await _grab()
	img.save_png(out_dir.path_join(name + ".png"))
	print("shot ", name, " ", img.get_size())


func _at_clock(t: float) -> void:
	main.paused_clock = true
	main.clock = t


func _hotspot(id: String) -> Dictionary:
	return main.data.hotspots.filter(func(h): return h.id == id)[0]


func _wait_until(cond: Callable, limit_s: float) -> float:
	var t := 0.0
	while not cond.call() and t < limit_s:
		await get_tree().process_frame
		t += get_process_delta_time()
	return t


func _run() -> void:
	await _frames(4)
	while not main.nav.ready_map():
		await get_tree().physics_frame
	await get_tree().physics_frame
	var win := get_window().size
	print("window %s, world viewport %s, frame %s" % [win, main.view.sv.size, main.view.frame])

	# zoom 0.5: the start of the intro, before the camera moves
	main.rig.set_view(main.rig.frame * 0.5, 0.5)
	var wide_ref = main.data.scene.get("views", {}).get("wide", {}).get("reference")
	if wide_ref:
		main.view.set_post(false)
		await _tonemap_check("", "zoom 0.5 vs the wide view's", wide_ref)
		main.view.set_post(true)
	await _shot("zoom050")
	main.overlay.visible = true
	await _shot("zoom050_overlay")
	main.overlay.visible = false
	await _frame_time("zoom 0.5")
	main.rig.set_view(main.rig.frame * 0.5, 1.0)
	main._on_view_settled()

	for h in main.data.hotspots:
		var s := SceneData.v3(h.stand)
		var snapped: Vector3 = main.nav.nav_point(s)
		print("stand %-12s offset %.2f m" % [h.id, Vector2(snapped.x - s.x, snapped.z - s.z).length()])
	var head: Vector2 = main.screen_of(Vector3(-2, 1.8, 2.2))
	var feet: Vector2 = main.screen_of(Vector3(-2, 0, 2.2))
	print("figure 1.8 m = %.1f frame px" % (feet.y - head.y))

	main.view.set_post(false)
	await _tonemap_check("reference", "tonemap")
	main.view.set_post(true)
	await _tonemap_check("reference_post", "post")
	await _frame_time("zoom 1")
	if "--checks" in OS.get_cmdline_user_args():
		get_tree().quit()
		return

	# zoom 1 and 2 with the figure by the gallows, with and without the walk overlay
	main.player.global_position = main.nav.nav_point(Vector3(3.0, 0.0, 3.6))
	main.player.face(Vector3(4.0, 0.0, 1.0))
	await _shot("zoom100")
	main.overlay.visible = true
	await _shot("zoom100_overlay")
	main.overlay.visible = false
	var gal := _hotspot("gallows")
	main.compositor.request_tile("gallows")
	await _wait_until(func(): return main.compositor.tile_ready("gallows"), 10.0)
	main.rig.set_view(main.compositor.tile_rect("gallows").get_center(), 2.0)
	var tile_ref = main.compositor.tile_defs["gallows"].get("reference")
	if tile_ref:
		main.view.set_post(false)
		await _tonemap_check("", "zoom 2 vs the gallows tile's", tile_ref)
		main.view.set_post(true)
	await _shot("zoom200_gallows")
	main.overlay.visible = true
	await _shot("zoom200_gallows_overlay")
	main.overlay.visible = false
	await _frame_time("zoom 2 (tile)")
	main.rig.set_view(main.rig.frame * 0.5, 1.0)

	# hover outline and Tab
	main.player.global_position = Vector3(-2.0, 0.0, 2.2)
	var well := _hotspot("well")
	var well_px: Vector2 = main.screen_of(SceneData.v3(well.position) + Vector3(0, 0.6, 0))
	main.update_hover(well_px)
	print("hover at the well kerb: %s" % _describe(main.interaction.hovered))
	await _shot("hover_well")
	main.interaction.set_tab(true)
	await _shot("tab_all")
	main.rig.set_view(main.compositor.tile_rect("well").get_center() if main.compositor.has_tile("well") else main.rig.frame * 0.5, 2.0)
	main.compositor.request_tile("well")
	await _wait_until(func(): return main.compositor.tile_ready("well"), 10.0)
	main.update_hover(main.screen_of(SceneData.v3(well.position) + Vector3(0, 0.6, 0)))
	await _shot("hover_well_zoom2")
	main.interaction.set_tab(false)
	main.rig.set_view(main.rig.frame * 0.5, 1.0)
	main.update_hover(Vector2(-100, -100))

	# click rule: what a click does at points on the gallows, the well, the cart and the stair
	var probes := {
		"gallows deck": Vector3(5.6, 1.6, 1.6), "gallows stair": Vector3(3.0, 0.85, 1.0),
		"gallows beam": Vector3(5.17, 4.45, 0.9), "gallows post": Vector3(3.9, 3.0, 0.5),
		"well kerb": SceneData.v3(well.position) + Vector3(0, 0.7, 0), "well roof": SceneData.v3(well.position) + Vector3(0, 2.4, 0),
		"cart bed": SceneData.v3(_hotspot("cart").position) + Vector3(0, 0.9, 0),
		"wall stair": Vector3(-9.8, 3.0, 0.8), "floor by the cart": Vector3(-1.8, 0.0, 4.6)}
	for k in probes:
		var px: Vector2 = main.screen_of(probes[k])
		var t: Dictionary = main.interaction.target_at(px)
		print("click rule: %-18s -> %s" % [k, _describe(t)])

	# gallows deck: click the boards, the figure walks onto the deck and no dialogue opens
	main.player.global_position = main.nav.nav_point(Vector3(2.0, 0.0, 3.5))
	Engine.time_scale = 3.0
	main.click(main.screen_of(Vector3(5.6, 1.6, 1.6)))
	await get_tree().create_timer(1.2).timeout
	await _shot("gallows_deck_walking")
	await _wait_until(func(): return not main.player.walking, 20.0)
	Engine.time_scale = 1.0
	print("gallows deck: figure at %s, dialogue open %s" % [main.player.global_position, main.ui.is_open()])
	await _shot("gallows_deck_on")

	# interaction: click the gallows beam, walk, zoom to 2 on the tile, close, zoom back
	Engine.time_scale = 3.0
	main.click(main.screen_of(Vector3(3.9, 3.0, 0.5)))
	await _wait_until(func(): return main.ui.is_open(), 20.0)
	Engine.time_scale = 1.0
	print("gallows dialogue open: %s" % main.ui.is_open())
	await get_tree().create_timer(3.0).timeout
	print("zoom after the interaction: %.2f, tile mix %.2f" % [main.rig.zoom, main.compositor.tile_mix])
	await _shot("interact_gallows_zoom2")
	main.ui.close()
	await get_tree().create_timer(3.0).timeout
	print("zoom after closing: %.2f" % main.rig.zoom)

	# footsteps: walk across the yard through a puddle and log the surfaces
	var steps := {}
	var logger := func(_foot): steps[main.audio.last_step] = steps.get(main.audio.last_step, 0) + 1
	main.player.step.connect(logger, CONNECT_DEFERRED)
	main.player.global_position = main.nav.nav_point(Vector3(-3.0, 0.0, 4.0))
	Engine.time_scale = 3.0
	main.player.walk_to(main.nav.nav_point(Vector3(1.6, 0.0, 0.6)))
	await _wait_until(func(): return not main.player.walking, 20.0)
	main.player.walk_to(main.nav.nav_point(Vector3(5.6, 1.6, 1.6)))
	await _wait_until(func(): return not main.player.walking, 20.0)
	Engine.time_scale = 1.0
	main.player.step.disconnect(logger)
	print("footstep surfaces: %s" % steps)

	# portal: from the yard, click the chamfer wall-walk; the figure climbs the stair, goes into
	# the NW tower and comes out on the wall-walk
	if not main.nav.portals.is_empty():
		var pt: Dictionary = main.nav.portals[0]
		main.player.global_position = main.nav.nav_point(Vector3(-8.0, 0.0, 5.0))
		var goal: Vector3 = pt.b + (Vector3(8.42, 6.0, -0.41) - pt.b).normalized() * 2.0
		Engine.time_scale = 4.0
		main.interaction._walk(main.nav.nav_point(goal))
		await _wait_until(func(): return main.portals.busy, 40.0)
		Engine.time_scale = 1.0
		await _shot("portal_enter")
		await get_tree().create_timer(1.5).timeout
		print("portal: figure visible inside: %s" % main.player.visible)
		await _shot("portal_inside")
		await _wait_until(func(): return not main.portals.busy, 10.0)
		await get_tree().create_timer(1.0).timeout
		print("portal: out at %s" % main.player.global_position)
		await _shot("portal_out")
		await _wait_until(func(): return not main.player.walking, 10.0)
		print("portal: on the wall-walk at %s" % main.player.global_position)
		Engine.time_scale = 4.0
		main.player.walk_to(main.nav.nav_point(Vector3(8.42, 6.0, -0.41)))
		await _wait_until(func(): return not main.player.walking, 20.0)
		Engine.time_scale = 1.0
		await _shot("wallwalk")
		print("wall-walk: figure at %s" % main.player.global_position)

	# the wall stair and an exit, as before
	Engine.time_scale = 4.0
	main.player.global_position = main.nav.nav_point(Vector3(-8.0, 0.0, 5.0))
	main.player.walk_to(main.nav.nav_point(Vector3(-9.8, 6.0, -1.0)))
	await get_tree().create_timer(2.0).timeout
	await _shot("stair_climbing")
	await _wait_until(func(): return not main.player.walking, 20.0)
	Engine.time_scale = 1.0
	await _crow_flight()
	get_tree().quit()


func _describe(t) -> String:
	if t == null:
		return "nothing"
	match t.kind:
		"hotspot":
			return "interact with %s%s" % [t.hotspot.id, " (walkable there)" if t.walkable else ""]
		"exit":
			return "exit %s" % t.exit.id
		"portal":
			return "portal %s" % t.portal.id
	return "walk%s" % (" (over %s)" % t.hotspot.id if t.get("hotspot") else "")


func _crow_flight() -> void:
	var near = null
	for c in main.crows.crows:
		if not c.flying and c.perch.pos.y < 2.5:
			near = c
			break
	if near == null:
		near = main.crows.crows[0]
	var p: Vector3 = near.perch.pos
	main.player.global_position = main.nav.nav_point(p + Vector3(4.5, 0, 0))
	await _frames(2)
	main.player.global_position = main.nav.nav_point(p + Vector3(1.5, 0, 0.5))
	await get_tree().create_timer(0.7).timeout
	print("crow %s flying: %s, at %s" % [near.name, near.flying, near.global_position])
	await _shot("crow_flight")


## Every group at intensity 1, nothing live on top: the screen must match reference.png without
## the post and reference_post.png with it.
func _tonemap_check(key: String, tag: String, ref_path = null) -> void:
	if ref_path == null:
		ref_path = main.data.scene.layers.get(key)
	if ref_path == null:
		return
	main.compositor.frozen = true
	main.set_rain(false)
	main.flipbooks.visible = false
	main.crows.visible = false
	main.player.visible = false
	var img := await _grab()
	img.convert(Image.FORMAT_RGB8)
	var ref := SceneData.image(ref_path)
	ref.convert(Image.FORMAT_RGB8)
	if ref.get_size() != img.get_size():
		print("tonemap check: screen %s, reference %s (rescaled, adds resampling error)" % [img.get_size(), ref.get_size()])
		ref.resize(img.get_width(), img.get_height(), Image.INTERPOLATE_CUBIC)
	var hist := PackedInt32Array()
	hist.resize(256)
	var total := 0.0
	var n := 0
	var worst := 0
	for y in range(0, img.get_height(), 2):
		for x in range(0, img.get_width(), 2):
			var a := img.get_pixel(x, y)
			var b := ref.get_pixel(x, y)
			var e := maxi(maxi(absi(a.r8 - b.r8), absi(a.g8 - b.g8)), absi(a.b8 - b.b8))
			total += (absi(a.r8 - b.r8) + absi(a.g8 - b.g8) + absi(a.b8 - b.b8)) / 3.0
			hist[e] += 1
			worst = maxi(worst, e)
			n += 1
	var p99 := 0
	var acc := 0
	for i in 256:
		acc += hist[i]
		if acc >= n * 0.99:
			p99 = i
			break
	var within1 := float(hist[0] + hist[1]) / n * 100.0
	print("%s check vs %s: mean |error| %.3f, p99 %d, max %d code values (8-bit); %.1f%% of pixels within 1" % [tag, ref_path.get_file(), total / n, p99, worst, within1])
	main.compositor.frozen = false
	main.set_rain(true)
	main.flipbooks.visible = true
	main.crows.visible = true
	main.player.visible = true


func _frame_time(tag: String) -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	var vp: RID = main.view.sv.get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(vp, true)
	await _frames(30)
	var times := []
	var gpu := 0.0
	var n := 240
	var last := Time.get_ticks_usec()
	for i in n:
		await RenderingServer.frame_post_draw
		var now := Time.get_ticks_usec()
		times.append((now - last) / 1000.0)
		gpu += RenderingServer.viewport_get_measured_render_time_gpu(vp)
		last = now
	times.sort()
	var mean := 0.0
	for x in times:
		mean += x
	mean /= n
	print("frame time %s at %s over %d frames: median %.2f ms, best %.2f ms, mean %.2f ms, p95 %.2f ms; world GPU %.2f ms" % [
		tag, main.view.sv.size, n, times[n / 2], times[0], mean, times[int(n * 0.95)], gpu / n])
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED)
