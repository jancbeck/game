## F1 overlay: proxy edges (walls cyan, props yellow), the walk mesh (green), hotspot stand
## points (red crosses) and exits (magenta), drawn over the frame with and without depth test.
extends Node3D

const SceneData := preload("res://scripts/scene_data.gd")


func setup(nav, hotspots: Array) -> void:
	visible = false
	var im := ImmediateMesh.new()
	im.surface_begin(Mesh.PRIMITIVE_LINES)
	var sets := []
	for entry in nav.proxy_meshes:
		if not entry[0].begins_with("floor"):
			sets.append([entry[1], Color(1.0, 0.85, 0.2) if entry[0].begins_with("prop") else Color(0.3, 1.0, 1.0)])
	sets.append([nav.walk_faces, Color(0.3, 1.0, 0.3)])
	for s in sets:
		for e in _feature_edges(s[0]):
			im.surface_set_color(s[1])
			im.surface_add_vertex(e[0])
			im.surface_set_color(s[1])
			im.surface_add_vertex(e[1])
	var marks := [[hotspots.map(func(h): return SceneData.v3(h.stand)), Color(1, 0.3, 0.3)],
		[nav.exits.map(func(e): return e.pos), Color(1, 0.3, 1)]]
	for m in marks:
		for s in m[0]:
			for d in [Vector3(0.25, 0, 0), Vector3(0, 0, 0.25), Vector3(0, 0.5, 0)]:
				im.surface_set_color(m[1])
				im.surface_add_vertex(s - d * (0.0 if d.y > 0 else 1.0))
				im.surface_set_color(m[1])
				im.surface_add_vertex(s + d)
	im.surface_end()
	for xray in [true, false]:
		var mat := StandardMaterial3D.new()
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mat.vertex_color_use_as_albedo = true
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.no_depth_test = xray
		mat.albedo_color = Color(1, 1, 1, 0.3 if xray else 1.0)
		mat.render_priority = 10 if xray else 11
		var mi := MeshInstance3D.new()
		mi.mesh = im
		mi.material_override = mat
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.extra_cull_margin = 1000.0
		add_child(mi)


## Edges where the surface folds (or ends), skipping the diagonals inside flat quads.
static func _feature_edges(faces: PackedVector3Array) -> Array:
	var edges := {}
	for i in range(0, faces.size(), 3):
		var a := faces[i]
		var b := faces[i + 1]
		var c := faces[i + 2]
		var n := (b - a).cross(c - a)
		if n.length() < 1e-9:
			continue
		n = n.normalized()
		for pair in [[a, b], [b, c], [c, a]]:
			var k := _edge_key(pair[0], pair[1])
			if not edges.has(k):
				edges[k] = [pair[0], pair[1], []]
			edges[k][2].append(n)
	var out := []
	for k in edges:
		var e: Array = edges[k]
		var ns: Array = e[2]
		if ns.size() != 2 or ns[0].dot(ns[1]) < 0.999:
			out.append([e[0], e[1]])
	return out


static func _edge_key(a: Vector3, b: Vector3) -> String:
	var ka := "%.3f,%.3f,%.3f" % [a.x, a.y, a.z]
	var kb := "%.3f,%.3f,%.3f" % [b.x, b.y, b.z]
	return ka + "|" + kb if ka < kb else kb + "|" + ka
