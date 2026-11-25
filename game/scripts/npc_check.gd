## Check run for people: talks to the first NPC (or `--npc-check=<id>`) and saves screenshots of
## the figure, a line in progress, a response picked, and the listening loop, with 3x crops around the
## person, and prints whether the player can walk to the person's stand point.
##   Godot --path game --audio-driver Dummy -- --no-intro --npc-check[=<id>]
## Extra flags: --npc-walk (the person walks a few metres at zoom 2: crops of the stride in
## game/shots/npc_walk_<k>.png, then the run ends), --swatches (flat grey swatches on the floor beside the
## frame's floor, to compare the figures' light with the render's).
extends Node

const SceneData := preload("res://scripts/scene_data.gd")


func _ready() -> void:
	var m := get_parent()
	await get_tree().create_timer(2.0).timeout
	var n = m.npcs[0]
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--npc-check="):
			n = m.npc_by_id(arg.substr(12))
	await _shot("npc_figure")
	_reach(m, n)
	if "--npc-walk" in OS.get_cmdline_user_args():
		await _walk(m, n)
		get_tree().quit()
		return
	if "--swatches" in OS.get_cmdline_user_args():
		await _swatches(m, n)
	await _crop("npc_figure_crop", n.figure.global_position + Vector3(0, 0.9, 0), 190)
	m.player.global_position = m.nav.nav_point(n.stand_point())
	m.interaction.pending = {npc = n}
	m.interaction._on_arrived()
	await get_tree().create_timer(2.5).timeout
	await _shot("npc_talking")
	await _crop("npc_talking_crop", (n.figure.global_position + m.player.global_position) * 0.5 + Vector3(0, 0.9, 0), 300)
	m.ui._pick(1)
	await get_tree().create_timer(3.0).timeout
	await _shot("npc_answer")
	await get_tree().create_timer(9.0).timeout
	await _shot("npc_listening")
	get_tree().quit()


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://shots"))
	get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path("res://shots/%s.png" % name))
	print("shot ", name)


## A crop around a world point (half size in screen px), scaled 3x with the nearest filter, for judging
## the figure's shading at the game's own pixel size.
func _crop(name: String, point: Vector3, half: int) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var s: Vector2 = get_parent().screen_of(point)
	var scale := float(img.get_width()) / float(get_viewport().get_visible_rect().size.x)
	var r := Rect2i(Vector2i((s * scale - Vector2(half, half * 1.15)).round()), Vector2i(half * 2, int(half * 2.3)))
	var c := img.get_region(r.intersection(Rect2i(Vector2i.ZERO, img.get_size())))
	c.resize(c.get_width() * 3, c.get_height() * 3, Image.INTERPOLATE_NEAREST)
	c.save_png(ProjectSettings.globalize_path("res://shots/%s.png" % name))
	print("crop ", name, " at ", s)


## Calibration of the figures' light against the frame: flat grey swatches (albedo 0.18, the figure
## shader's own shading) on the floor around the person, each next to a bare floor patch; prints the display
## colour of both, and saves npc_swatches.png. A swatch that matches the floor beside it shows that the
## real-time light and the ambient agree with the render for a mid-grey surface.
func _swatches(m: Node, n) -> void:
	var FigureLook := preload("res://scripts/figure_look.gd")
	var spots: Array[Vector3] = []
	for d in [Vector2(2.2, 1.6), Vector2(3.2, 0.2), Vector2(0.0, 1.0), Vector2(-0.4, 0.2), Vector2(1.2, 0.3), Vector2(4.2, 1.4)]:
		spots.append(n.figure.global_position + Vector3(d.x, 0.0, d.y))
	var boxes := []
	for p in spots:
		var q: Vector3 = m.nav.nav_point(p)
		var mi := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = Vector3(0.45, 0.02, 0.45)
		mi.mesh = bm
		var sm := StandardMaterial3D.new()
		sm.resource_name = "skin"
		var mat: ShaderMaterial = FigureLook.material(sm)
		mat.set_shader_parameter("part", 1)
		mat.set_shader_parameter("tint", Vector3(0.18, 0.18, 0.18))
		mi.material_override = mat
		m.world.add_child(mi)
		mi.global_position = q + Vector3(0, 0.012, 0)
		boxes.append(q)
	await get_tree().create_timer(0.4).timeout
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	var scale := float(img.get_width()) / float(get_viewport().get_visible_rect().size.x)
	for q in boxes:
		var c: Vector2 = m.screen_of(q + Vector3(0, 0.02, 0)) * scale
		var nb: Vector2 = m.screen_of(q + Vector3(0.7, 0.0, 0.0)) * scale
		print("swatch at ", q, " display ", _avg(img, c), " floor beside ", _avg(img, nb))
	img.save_png(ProjectSettings.globalize_path("res://shots/npc_swatches.png"))


func _avg(img: Image, c: Vector2) -> Color:
	var sum := Color(0, 0, 0)
	var k := 0
	for dx in range(-3, 4):
		for dy in range(-3, 4):
			var px := Vector2i(int(c.x) + dx, int(c.y) + dy)
			if Rect2i(Vector2i.ZERO, img.get_size()).has_point(px):
				sum += img.get_pixelv(px)
				k += 1
	return Color(snappedf(sum.r / k, 0.01), snappedf(sum.g / k, 0.01), snappedf(sum.b / k, 0.01))


## The person walks a few metres at zoom 2: crops of the stride, to see the skirt or cloak around the legs.
func _walk(m: Node, n) -> void:
	var start: Vector3 = n.figure.global_position
	var goal: Vector3 = start
	for off in [Vector3(2.4, 0, 0.15), Vector3(-2.0, 0, 0.3), Vector3(0, 0, 2.5), Vector3(2.4, 0, 1.8), Vector3(-2.0, 0, -1.5)]:
		var cand: Vector3 = m.nav.nav_point(start + off)
		var pts: PackedVector3Array = m.nav.path(start, cand)
		var length := 0.0
		for i in range(1, pts.size()):
			length += pts[i - 1].distance_to(pts[i])
		print("walk candidate ", cand, " path of ", snappedf(length, 0.1), " m")
		if length > 1.8:
			goal = cand
			break
	if goal == start:
		# a person fenced in by props has no path: walk a straight line, only to look at the stride
		n.figure._path = PackedVector3Array([start, start + Vector3(-2.6, 0.0, 0.0)])
		n.figure._next = 1
		n.figure.walking = true
		print("walking in a straight line, off the navmesh")
	else:
		print("walking: ", n.figure.walk_to(goal), " to ", goal)
	await get_tree().create_timer(0.3).timeout
	for k in 8:
		var p: Vector3 = n.figure.global_position + Vector3(0, 0.8, 0)
		m.rig.set_view(m.rig.frame_px_of(p), 2.0)
		var keys := ""
		if n.figure._fit_mesh != null:
			for key in n.figure._fit_index:
				var v: float = n.figure._fit_mesh.get_blend_shape_value(n.figure._fit_index[key])
				if v > 0.01:
					keys += " %s=%.2f" % [key, v]
		print("figure at ", n.figure.global_position, " walking ", n.figure.walking, " shape keys on:", keys)
		await _crop("npc_walk_%d" % k, p, 300)
		await get_tree().create_timer(0.1).timeout


## Prints whether the player can walk from where the location puts them to the person's stand point (the
## navmesh has the props carved out with the agent's radius): a stand point inside a prop or behind one fails.
func _reach(m: Node, n) -> void:
	var from: Vector3 = m.player.global_position
	var exits: Array = m.data.scene.get("walk", {}).get("exits", [])
	if m.data.location != "courtyard" and not exits.is_empty():
		from = SceneData.v3(exits[0].pos)         # an interior: the player comes in by its door
	var to: Vector3 = n.stand_point()
	var pts: PackedVector3Array = m.nav.path(from, to)
	var length := 0.0
	for i in range(1, pts.size()):
		length += pts[i - 1].distance_to(pts[i])
	var end: Vector3 = pts[pts.size() - 1] if pts.size() > 0 else from
	print("stand point of ", n.def.id, " ", to, ": path of ", snappedf(length, 0.1), " m ends ", snappedf(Vector2(end.x - to.x, end.z - to.z).length(), 0.01), " m from it; the person stands ", snappedf(Vector2(n.figure.global_position.x - to.x, n.figure.global_position.z - to.z).length(), 0.01), " m from it")
