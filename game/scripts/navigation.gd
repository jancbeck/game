## Walkable space: a navmesh baked at start from walk.glb (floor, gate passage, stairs, landings,
## the gallows deck), navigation links, prop footprints carved from the ground, and the exits.
##
## scene.json -> walk {mesh, links [{from, to, kind}], exits [{id, pos, label, target}],
## portals [{id, a, b, label, label_b, seconds, sound, via}]}; a portal with "to": "<location>" is a
## door out to that location (end `a` only; the figure leaves the scene through it). walk.glb faces carry a material named after the
## surface (cobble, mud, stone_stair, stone_walk, wood, straw); surface_at() finds it under a foot.
## scene.json -> proxy: prop_* hulls carve the ground around props, except where walk.glb has a
## raised surface inside the hull (the gallows deck and stair, the wall stair): there the walk
## mesh alone decides.
extends Node3D

const SceneData := preload("res://scripts/scene_data.gd")
const CELL := 0.1
const CELL_H := 0.05

var region: NavigationRegion3D
var nav_height := 0.0          # how far the navmesh polygons sit above the surface
var walk_faces := PackedVector3Array()
var proxy_meshes: Array = []   # [name, PackedVector3Array faces in world space]
var exits: Array = []          # [{id, pos: Vector3, label, target}]
var portals: Array = []        # [{id, a: Vector3, b: Vector3, label, to, seconds, sound}]
var _iteration_before := 0     # the map's iteration before this navmesh was added
var _probe := Vector3.ZERO     # a point of the navmesh: an unsynced map answers with the origin
var _surf_tris := PackedVector3Array()
var _surf_names: Array[String] = []    # one per triangle
var _surf_grid := {}                   # Vector2i cell -> triangle indices
const SURF_CELL := 1.0


func setup(data: SceneData) -> void:
	var walk: Dictionary = data.scene.get("walk", {})
	if data.has("proxy"):
		proxy_meshes = _load_glb_faces(data.scene.proxy, true)
	if walk.get("mesh"):
		for entry in _load_glb_faces(walk.mesh, false):
			walk_faces.append_array(entry[1])
			_add_surface(entry[2], entry[1])
	else:
		# round-18 data: the proxy floor is all there is
		for entry in proxy_meshes:
			if entry[0].begins_with("floor"):
				walk_faces.append_array(entry[1])
	for pt in walk.get("portals", []):
		var a := SceneData.v3(pt.a)
		portals.append({id = pt.id, a = a, b = SceneData.v3(pt.b) if pt.has("b") else a, label = pt.get("label", pt.id),
			label_b = pt.get("label_b", pt.get("label", pt.id)), to = pt.get("to", pt.get("target", "")),
			seconds = float(pt.get("seconds", 3.0)), sound = pt.get("sound", "")})
	for e in walk.get("exits", []):
		var pos := SceneData.v3(e.pos)
		# a door that is a portal end is not also an exit
		if portals.any(func(pt): return pos.distance_to(pt.a) < 1.5 or pos.distance_to(pt.b) < 1.5):
			continue
		exits.append({id = e.id, pos = pos, label = e.get("label", e.id), target = e.get("target", "")})
	_bake()
	for l in walk.get("links", []):
		var link := NavigationLink3D.new()
		link.start_position = SceneData.v3(l.from)
		link.end_position = SceneData.v3(l.to)
		link.bidirectional = true
		add_child(link)


func _load_glb_faces(path: String, keep_nodes: bool) -> Array:
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	if doc.append_from_file(SceneData.abs_path(path), state) != OK:
		push_error("cannot load glTF " + path)
		return []
	var root := doc.generate_scene(state)
	add_child(root)
	var out := []
	for mi in root.find_children("*", "MeshInstance3D", true, false):
		var xf: Transform3D = mi.global_transform
		var mesh: Mesh = mi.mesh
		for si in mesh.get_surface_count():
			var arrays := mesh.surface_get_arrays(si)
			var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var idx = arrays[Mesh.ARRAY_INDEX]
			var faces := PackedVector3Array()
			if idx == null or idx.is_empty():
				for v in verts:
					faces.append(xf * v)
			else:
				for i in idx:
					faces.append(xf * verts[i])
			var m := mesh.surface_get_material(si)
			var surf := m.resource_name if m and m.resource_name != "" else ""
			out.append([String(mi.name), faces, surf])
		if keep_nodes and not String(mi.name).begins_with("floor"):
			# invisible, but walls and props still shadow the real-time figure
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
		else:
			mi.visible = false
	if not keep_nodes:
		root.queue_free()
	return out


func _bake() -> void:
	var nm := NavigationMesh.new()
	nm.cell_size = CELL
	nm.cell_height = CELL_H
	nm.agent_radius = 0.3
	nm.agent_height = 1.8
	nm.agent_max_climb = 0.3
	nm.agent_max_slope = 50.0
	nm.region_min_size = 1.0
	nm.detail_sample_distance = 2.0
	nm.detail_sample_max_error = 0.5
	var src := NavigationMeshSourceGeometryData3D.new()
	src.add_faces(walk_faces, Transform3D.IDENTITY)
	var carved := 0
	for entry in proxy_meshes:
		if not entry[0].begins_with("prop"):
			continue
		var faces: PackedVector3Array = entry[1]
		var flat := PackedVector2Array()
		var lo := INF
		for v in faces:
			flat.append(Vector2(v.x, v.z))
			lo = minf(lo, v.y)
		var hull := Geometry2D.convex_hull(flat)
		if _has_raised_walk(hull, lo):
			continue
		hull.remove_at(hull.size() - 1)
		var outline := PackedVector3Array()
		for p in hull:
			outline.append(Vector3(p.x, 0.0, p.y))
		# only the ground band: raised walkways over or beside a prop stay walkable
		src.add_projected_obstruction(outline, lo - 0.5, 1.2, false)
		carved += 1
	NavigationServer3D.bake_from_source_geometry_data(nm, src)
	var map := get_world_3d().navigation_map
	_iteration_before = NavigationServer3D.map_get_iteration_id(map)
	if nm.get_vertices().size() > 0:
		_probe = nm.get_vertices()[0]
	region = NavigationRegion3D.new()
	region.navigation_mesh = nm
	add_child(region)
	NavigationServer3D.map_set_cell_size(map, CELL)
	NavigationServer3D.map_set_cell_height(map, CELL_H)
	# recast puts the polygons up to a cell above the surface; measure it on the flat floor
	nav_height = INF
	var lo_y := INF
	var hi_y := -INF
	for v in nm.get_vertices():
		if absf(v.y) < 0.3:
			nav_height = minf(nav_height, v.y)
		lo_y = minf(lo_y, v.y)
		hi_y = maxf(hi_y, v.y)
	if nav_height == INF:
		nav_height = 0.0
	print("navmesh: %d polygons, %.2f..%.2f m high, %.2f m above the floor, %d props carved" % [
		nm.get_polygon_count(), lo_y, hi_y, nav_height, carved])


func _has_raised_walk(hull: PackedVector2Array, ground: float) -> bool:
	for i in range(0, walk_faces.size(), 3):
		var c := (walk_faces[i] + walk_faces[i + 1] + walk_faces[i + 2]) / 3.0
		if c.y > ground + 0.3 and Geometry2D.is_point_in_polygon(Vector2(c.x, c.z), hull):
			return true
		for k in 3:
			var v := walk_faces[i + k]
			if v.y > ground + 0.3 and Geometry2D.is_point_in_polygon(Vector2(v.x, v.z), hull):
				return true
	return false


func _add_surface(name: String, faces: PackedVector3Array) -> void:
	for i in range(0, faces.size(), 3):
		var k := _surf_names.size()
		_surf_tris.append(faces[i])
		_surf_tris.append(faces[i + 1])
		_surf_tris.append(faces[i + 2])
		_surf_names.append(name)
		var lo := Vector2(minf(faces[i].x, minf(faces[i + 1].x, faces[i + 2].x)), minf(faces[i].z, minf(faces[i + 1].z, faces[i + 2].z)))
		var hi := Vector2(maxf(faces[i].x, maxf(faces[i + 1].x, faces[i + 2].x)), maxf(faces[i].z, maxf(faces[i + 1].z, faces[i + 2].z)))
		for cx in range(floori(lo.x / SURF_CELL), floori(hi.x / SURF_CELL) + 1):
			for cz in range(floori(lo.y / SURF_CELL), floori(hi.y / SURF_CELL) + 1):
				var key := Vector2i(cx, cz)
				if not _surf_grid.has(key):
					_surf_grid[key] = PackedInt32Array()
				_surf_grid[key].append(k)


## Surface name of the walk mesh under a foot ("" when walk.glb has no surface materials).
func surface_at(p: Vector3) -> String:
	var key := Vector2i(floori(p.x / SURF_CELL), floori(p.z / SURF_CELL))
	var best := ""
	var best_dy := 0.6
	var q := Vector2(p.x, p.z)
	for k in _surf_grid.get(key, PackedInt32Array()):
		var a := _surf_tris[k * 3]
		var b := _surf_tris[k * 3 + 1]
		var c := _surf_tris[k * 3 + 2]
		if not Geometry2D.point_is_inside_triangle(q, Vector2(a.x, a.z), Vector2(b.x, b.z), Vector2(c.x, c.z)):
			continue
		var dy := absf((a.y + b.y + c.y) / 3.0 - p.y)
		if dy < best_dy:
			best_dy = dy
			best = _surf_names[k]
	return best


## True when a path from `from` reaches `to` (within 0.35 m).
func reachable(from: Vector3, to: Vector3) -> bool:
	var pts := path(from, to)
	return pts.size() >= 2 and pts[pts.size() - 1].distance_to(to) < 0.35 or from.distance_to(to) < 0.1


## Closest walkable point to p, on whichever level is nearest in 3D.
func nav_point(p: Vector3) -> Vector3:
	return NavigationServer3D.map_get_closest_point(get_world_3d().navigation_map, p)


func path(from: Vector3, to: Vector3) -> PackedVector3Array:
	var pts := NavigationServer3D.map_get_path(get_world_3d().navigation_map, from + Vector3.UP * nav_height, to, true)
	for i in pts.size():
		pts[i].y -= nav_height
	return pts


## True once the map has synced with this navmesh (the world's map may be older than it, and
## its first sync may come before the navmesh is in).
func ready_map() -> bool:
	var map := get_world_3d().navigation_map
	return NavigationServer3D.map_get_iteration_id(map) > _iteration_before \
			and NavigationServer3D.map_get_closest_point(map, _probe) != Vector3.ZERO


## The exit whose doorway a world point lies in or near (for hover and clicks), or null.
func exit_near(p: Vector3, reach := 1.3):
	for e in exits:
		var d: Vector3 = p - e.pos
		if Vector2(d.x, d.z).length() < reach and d.y > -0.6 and d.y < 3.0:
			return e
	return null
