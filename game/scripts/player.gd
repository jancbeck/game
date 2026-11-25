## A garrison man: a 1.8 m figure that walks the navmesh at 1.75 m/s, on any level.
##
## The figure is a skinned GLB from characters/<model>/recipe.json (assets/characters/<model>.glb
## and <model>.json, built by scripts/make_character.py) with idle, talk and walk clips, and any
## others the recipe names (idle_clip picks the one played while standing). The walk
## clip is baked for SPEED, so its feet stay on the ground at 1:1 playback; `step` fires at the
## clip's heel strikes with the foot's position, for the footstep sounds. Without the GLB the
## figure is the procedural one: capsules swung at STEP_M per step.
extends Node3D

signal arrived
signal step(foot: Vector3)

const SPEED := 1.75         # m/s along the ground
const STEP_M := 0.78        # step length at SPEED (a brisk walk for a 1.8 m man)
const CLIMB := 0.6          # m/s on a ladder (a link with little horizontal run)
const TURN_RATE := 10.0
const SceneData := preload("res://scripts/scene_data.gd")
const FigureLook := preload("res://scripts/figure_look.gd")
const CHARACTER_DIR := "assets/characters/"
const BLEND_S := 0.22       # seconds to blend between idle, talk and walk
const LEAN_PER_YAW_RATE := 0.012   # rad of lean into a turn per rad/s of yaw rate, at most MAX_LEAN
const MAX_LEAN := 0.07

var nav                     # navigation.gd
var model := "player"       # characters/<model>/recipe.json; "" for the procedural figure
var idle_clip := "idle"     # the clip played when standing: "stir" for a cook, "sleep" for a sleeper
var talk_clip := "talk"     # the clip blended in while a line plays: "sit_talk" for a person at a desk
## Colours for the procedural figure: wool, jerkin, hose, skin, hood. A skinned figure takes its
## colours from its recipe; palette.tint (a Color) multiplies the cloth.
var palette := {}
var walking := false
var talking := false        # NPCs: gesture while a line plays
var _path := PackedVector3Array()
var _next := 0
var _phase := 0.0
var _legs: Array[Node3D] = []
var _arms: Array[Node3D] = []

# skinned figure
var _visual: Node3D         # the glTF scene, turned so its front faces -Z
var _tree: AnimationTree
var _meta := {}
var _walk_clock := 0.0
var _moving := false        # was the figure moving last frame
var _w_walk := 0.0
var _w_talk := 0.0
var _yaw_rate := 0.0
var _last_yaw := 0.0
var _speed_ratio := 1.0     # distance covered this tick over SPEED * delta: 1 on the flat, less on a ladder

# floor shadow (shaders/figure_shadow.gdshader); lights.gd feeds it the lamps near the figure
var shadow_mat: ShaderMaterial
var body_height := 1.7
var body_radius := 0.2

# free cloth (characters/posefit.py): shape keys of the skirt or cloak, switched on with the clips
var _fit := {}              # <id>.json "fit": clip -> {keys, frames, frame_count, mode}
var _fit_mesh: MeshInstance3D
var _fit_index := {}        # shape key name -> blend shape index
var _idle_name := "idle"
var _talk_name := "talk"
var _skins: Array[ShaderMaterial] = []     # the figure shader materials, for per-frame parameters


func has_model() -> bool:
	return _visual != null


func _ready() -> void:
	add_to_group("figures")
	if "--procedural-figures" in OS.get_cmdline_user_args():
		model = ""
	if model == "" or not _load_model():
		_build_body()
	_build_shadow()
	if _visual != null:
		_size_shadow()


## The floor shadow: a quad on the floor under the figure, depth-tested against the frame.
func _build_shadow() -> void:
	var quad := QuadMesh.new()
	quad.size = Vector2(4.4, 4.4)
	quad.orientation = PlaneMesh.FACE_Y
	var blob := MeshInstance3D.new()
	blob.name = "FloorShadow"
	blob.mesh = quad
	shadow_mat = ShaderMaterial.new()
	shadow_mat.shader = load("res://shaders/figure_shadow.gdshader")
	shadow_mat.set_shader_parameter("shade", Vector3(FigureLook.shade.r, FigureLook.shade.g, FigureLook.shade.b))
	blob.material_override = shadow_mat
	blob.position.y = 0.02
	blob.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	blob.extra_cull_margin = 4.0
	add_child(blob)


## The mesh with the shape keys of the free cloth, and their indices.
func _find_fit_keys(node: Node) -> void:
	if node is MeshInstance3D and _fit_mesh == null:
		var mi: MeshInstance3D = node
		if mi.mesh != null and mi.mesh.get_blend_shape_count() > 0:
			_fit_mesh = mi
			for i in mi.mesh.get_blend_shape_count():
				_fit_index[String(mi.mesh.get_blend_shape_name(i))] = i
			return
	for c in node.get_children():
		_find_fit_keys(c)


## Shape keys of the cloth for the clips playing: a standing clip with a drape key has it on, the walk
## clip blends its two keys nearest the phase of the stride.
func _update_fit() -> void:
	if _fit_mesh == null or _fit.is_empty():
		return
	var weights := {}
	var standing := 1.0 - _w_walk
	_fit_hold(_idle_name, (1.0 - _w_talk) * standing, weights)
	_fit_hold(_talk_name, _w_talk * standing, weights)
	var wf: Dictionary = _fit.get("walk", {})
	if not wf.is_empty() and _w_walk > 0.001:
		var keys: Array = wf.keys
		var n := keys.size()
		var period: float = _meta.get("animations", {}).get("walk", {}).get("period_s", 0.8)
		var phase := fposmod(_walk_clock, period) / period * float(n)
		var i0 := int(floorf(phase)) % n
		var f := phase - floorf(phase)
		var a: String = keys[i0]
		var b: String = keys[(i0 + 1) % n]
		weights[a] = float(weights.get(a, 0.0)) + (1.0 - f) * _w_walk
		weights[b] = float(weights.get(b, 0.0)) + f * _w_walk
	for key in _fit_index:
		_fit_mesh.set_blend_shape_value(_fit_index[key], float(weights.get(key, 0.0)))


func _fit_hold(clip: String, w: float, weights: Dictionary) -> void:
	var f: Dictionary = _fit.get(clip, {})
	if f.get("mode", "") == "drape":
		var k: String = f.keys[0]
		weights[k] = float(weights.get(k, 0.0)) + w


## A lying figure (a clip with a footprint) casts a pool on the floor, not a standing shadow.
func _size_shadow() -> void:
	var clip: Dictionary = _meta.get("animations", {}).get(idle_clip, {})
	if clip.has("footprint_m"):
		var fp: Array = clip.footprint_m
		body_height = 0.0
		shadow_mat.set_shader_parameter("pool_size", Vector2(float(fp[0]) * 0.55, float(fp[1]) * 0.55))
		shadow_mat.set_shader_parameter("pool", 0.5)


## Called by lights.gd every frame: the light the floor under the figure throws back up at it.
func set_bounce(c: Color, fill: Color) -> void:
	for m in _skins:
		m.set_shader_parameter("bounce", Vector3(c.r, c.g, c.b))
		m.set_shader_parameter("fill", Vector3(fill.r, fill.g, fill.b))


## Called by lights.gd every frame: the lamps (xyz, weight) whose light this figure blocks.
func set_shadow_lamps(a: Vector4, b: Vector4, c: Vector4) -> void:
	shadow_mat.set_shader_parameter("foot", global_position)
	shadow_mat.set_shader_parameter("pool_yaw", rotation.y)
	shadow_mat.set_shader_parameter("body_height", body_height)
	shadow_mat.set_shader_parameter("body_radius", body_radius)
	shadow_mat.set_shader_parameter("lamp_a", a)
	shadow_mat.set_shader_parameter("lamp_b", b)
	shadow_mat.set_shader_parameter("lamp_c", c)


## Walk the navmesh path to target; returns false when there is no path.
func walk_to(target: Vector3) -> bool:
	_path = nav.path(global_position, target)
	_next = 1
	walking = _path.size() >= 2
	return walking


func stop() -> void:
	walking = false
	_path = PackedVector3Array()


func face(point: Vector3) -> void:
	var d := point - global_position
	d.y = 0.0
	if d.length() > 0.01:
		rotation.y = atan2(-d.x, -d.z)


## Follows the path polyline in 3D, so the feet go up stairs and ramps with the path's heights.
func _physics_process(delta: float) -> void:
	_yaw_rate = angle_difference(_last_yaw, rotation.y) / maxf(delta, 0.0001)
	_last_yaw = rotation.y
	if not walking:
		_animate(delta, false)
		return
	var budget := SPEED * delta
	var moved := false
	var start := global_position
	while budget > 0.0 and _next < _path.size():
		var target := _path[_next]
		var d := target - global_position
		var run := Vector2(d.x, d.z).length()
		if run > 0.001:
			var dir := Vector3(d.x, 0.0, d.z) / run
			rotation.y = lerp_angle(rotation.y, atan2(-dir.x, -dir.z), minf(1.0, delta * TURN_RATE))
		# horizontal speed on the ground; a near-vertical step (ladder) climbs at CLIMB
		var cost := run if run > absf(d.y) * 0.3 else absf(d.y) * SPEED / CLIMB
		if cost <= budget:
			global_position = target
			budget -= cost
			_next += 1
		else:
			global_position += d * (budget / cost)
			budget = 0.0
		moved = true
	_speed_ratio = clampf(start.distance_to(global_position) / maxf(delta * SPEED, 0.0001), 0.35, 1.1)
	_animate(delta, moved)
	if _next >= _path.size():
		walking = false
		arrived.emit()


func _animate(delta: float, moving: bool) -> void:
	if _visual != null:
		_animate_skinned(delta, moving)
		return
	if moving:
		var before := floori(_phase / PI)
		_phase += delta * SPEED / STEP_M * PI  # one step per half cycle
		if floori(_phase / PI) != before:
			# the leading leg is the one that swung forward; its foot lands ahead of the hips
			var side := 0.1 if (floori(_phase / PI) % 2 == 0) else -0.1
			step.emit(global_position + global_basis * Vector3(side, 0.0, -0.25))
	else:
		_phase = lerp(_phase, round(_phase / PI) * PI, min(1.0, delta * 8.0))
	var swing := sin(_phase) * 0.45
	for i in _legs.size():
		_legs[i].rotation.x = swing * (1.0 if i == 0 else -1.0)
	for i in _arms.size():
		_arms[i].rotation.x = -swing * 0.7 * (1.0 if i == 0 else -1.0)


## The talk gesture follows the voice: NPCs call this when a line starts and ends.
func set_talking(on: bool) -> void:
	talking = on


# ---------- the skinned figure ----------

## Loads assets/characters/<model>.glb at run time (the asset folders are not imported).
## Returns false, leaving the procedural figure to the caller, when the file is missing.
func _load_model() -> bool:
	var path := SceneData.abs_path(CHARACTER_DIR + model + ".glb")
	if not FileAccess.file_exists(path):
		return false
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	if doc.append_from_file(path, state) != OK:
		push_warning("cannot load character " + model)
		return false
	var meta_path := SceneData.res(CHARACTER_DIR + model + ".json")
	if FileAccess.file_exists(meta_path):
		_meta = JSON.parse_string(FileAccess.get_file_as_string(meta_path))
	body_height = float(_meta.get("height_m", body_height))
	body_radius = float(_meta.get("radius_m", body_radius * 0.9)) * 1.1
	_fit = _meta.get("fit", {})
	var root: Node3D = doc.generate_scene(state)
	var anim: AnimationPlayer = root.find_child("AnimationPlayer", true, false)
	if anim == null or not anim.has_animation("walk") or not anim.has_animation("idle"):
		root.free()
		return false
	# the model faces +Z (glTF); the figure's front is -Z
	_visual = Node3D.new()
	_visual.name = "Visual"
	_visual.rotation.y = PI
	add_child(_visual)
	_visual.add_child(root)
	for n in anim.get_animation_list():
		anim.get_animation(n).loop_mode = Animation.LOOP_LINEAR
	_setup_tree(root, anim)
	_style_materials(root)
	_find_fit_keys(root)
	return true


## idle -> talk -> walk, as two blends. All clips run at all times (sync), so the walk is in
## step with `_walk_clock`, which the footsteps follow.
func _setup_tree(root: Node3D, anim: AnimationPlayer) -> void:
	var bt := AnimationNodeBlendTree.new()
	var names := ["idle", "talk", "walk"]
	for n in names:
		var node := AnimationNodeAnimation.new()
		var clip: String = idle_clip if n == "idle" else (talk_clip if n == "talk" else n)
		node.animation = clip if anim.has_animation(clip) else "idle"
		if n == "idle":
			_idle_name = node.animation
		elif n == "talk":
			_talk_name = node.animation
		bt.add_node(n, node)
	var scale := AnimationNodeTimeScale.new()
	bt.add_node("walk_scale", scale)
	bt.connect_node("walk_scale", 0, "walk")
	var seek := AnimationNodeTimeSeek.new()
	bt.add_node("walk_seek", seek)
	bt.connect_node("walk_seek", 0, "walk_scale")
	var talk_mix := AnimationNodeBlend2.new()
	talk_mix.sync = true
	bt.add_node("talk_mix", talk_mix)
	bt.connect_node("talk_mix", 0, "idle")
	bt.connect_node("talk_mix", 1, "talk")
	var walk_mix := AnimationNodeBlend2.new()
	walk_mix.sync = true
	bt.add_node("walk_mix", walk_mix)
	bt.connect_node("walk_mix", 0, "talk_mix")
	bt.connect_node("walk_mix", 1, "walk_seek")
	bt.connect_node("output", 0, "walk_mix")
	_tree = AnimationTree.new()
	_tree.name = "AnimationTree"
	_tree.tree_root = bt
	_tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_PHYSICS
	root.add_child(_tree)
	_tree.anim_player = _tree.get_path_to(anim)
	_tree.active = true


## The figure shader for every surface (cloth, leather, linen, hair, skin, eyes): see figure.gdshader.
## palette.tint (a Color) multiplies the cloth.
func _style_materials(node: Node) -> void:
	if node is MeshInstance3D:
		var mi: MeshInstance3D = node
		for s in mi.mesh.get_surface_count():
			var src: Material = mi.mesh.surface_get_material(s)
			if src is StandardMaterial3D:
				var mat := FigureLook.material(src, palette.get("tint"))
				_skins.append(mat)
				mi.set_surface_override_material(s, mat)
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	for c in node.get_children():
		_style_materials(c)


func _animate_skinned(delta: float, moving: bool) -> void:
	var walk: Dictionary = _meta.get("animations", {}).get("walk", {})
	var period: float = walk.get("period_s", 0.8333)
	if moving and not _moving:
		# start from the pose where the legs pass, close to standing
		_walk_clock = walk.get("pass_phase_s", 0.0)
		_tree.set("parameters/walk_seek/seek_request", _walk_clock)
	var before := _walk_clock
	# the clip is baked for SPEED; on a ladder the feet march slower, in step with the climb
	_tree.set("parameters/walk_scale/scale", _speed_ratio if moving else 1.0)
	if moving:
		_walk_clock += delta * _speed_ratio
		for t in walk.get("contacts", []):
			if _crossed(before, _walk_clock, float(t), period):
				var side := -0.1 if t == walk.contacts[0] else 0.1     # contacts[0] is the left foot (-X, facing -Z)
				step.emit(global_position + global_basis * Vector3(side, 0.0, -0.2))
	_moving = moving
	_w_walk = move_toward(_w_walk, 1.0 if moving else 0.0, delta / BLEND_S)
	_w_talk = move_toward(_w_talk, 1.0 if talking and not moving else 0.0, delta / (BLEND_S * 2.0))
	_tree.set("parameters/walk_mix/blend_amount", _w_walk)
	_tree.set("parameters/talk_mix/blend_amount", _w_talk)
	# the body leans into a turn (the visual is turned PI about Y, so its roll is mirrored)
	var lean := clampf(_yaw_rate * LEAN_PER_YAW_RATE, -MAX_LEAN, MAX_LEAN) if moving else 0.0
	_visual.rotation.z = lerpf(_visual.rotation.z, -lean, minf(1.0, delta * 8.0))
	_update_fit()


## True when the clip time passed `at` (seconds into the cycle) between a and b.
func _crossed(a: float, b: float, at: float, period: float) -> bool:
	return floorf((b - at) / period) > floorf((a - at) / period)


## Cloth and leather with a rim from lights behind the figure, so the fire it faces outlines it.
func _mat(color: Color, rough := 0.85) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = rough
	m.rim_enabled = true
	m.rim = 0.3
	m.rim_tint = 0.3
	return m


func _part(mesh: Mesh, mat: Material, pos: Vector3, parent: Node3D = self) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	parent.add_child(mi)
	return mi


func _capsule(r: float, h: float) -> CapsuleMesh:
	var c := CapsuleMesh.new()
	c.radius = r
	c.height = h
	c.radial_segments = 10
	c.rings = 3
	return c


## Head top at 1.80 m. Wool tunic, leather jerkin, hood, dark hose and boots.
func _build_body() -> void:
	var wool := _mat(palette.get("wool", Color(0.30, 0.27, 0.22)))
	var jerkin := _mat(palette.get("jerkin", Color(0.22, 0.15, 0.10)), 0.7)
	var hose := _mat(palette.get("hose", Color(0.16, 0.16, 0.17)))
	var boots := _mat(Color(0.10, 0.08, 0.06), 0.6)
	var skin := _mat(palette.get("skin", Color(0.62, 0.45, 0.36)), 0.6)
	var hood := _mat(palette.get("hood", Color(0.25, 0.27, 0.24)))
	for side in [-1.0, 1.0]:
		var hip := Node3D.new()
		hip.position = Vector3(0.1 * side, 0.9, 0.0)
		add_child(hip)
		_part(_capsule(0.075, 0.85), hose, Vector3(0, -0.43, 0), hip)
		var boot := BoxMesh.new()
		boot.size = Vector3(0.11, 0.1, 0.26)
		_part(boot, boots, Vector3(0, -0.85, -0.05), hip)
		_legs.append(hip)
	var torso := _capsule(0.2, 0.72)
	_part(torso, wool, Vector3(0, 1.22, 0))
	var vest := BoxMesh.new()
	vest.size = Vector3(0.36, 0.42, 0.26)
	_part(vest, jerkin, Vector3(0, 1.3, 0))
	var belt := CylinderMesh.new()
	belt.top_radius = 0.205
	belt.bottom_radius = 0.205
	belt.height = 0.05
	_part(belt, boots, Vector3(0, 1.05, 0))
	for side in [-1.0, 1.0]:
		var shoulder := Node3D.new()
		shoulder.position = Vector3(0.25 * side, 1.47, 0.0)
		add_child(shoulder)
		_part(_capsule(0.055, 0.62), wool, Vector3(0, -0.29, 0), shoulder)
		var hand := SphereMesh.new()
		hand.radius = 0.045
		hand.height = 0.09
		_part(hand, skin, Vector3(0, -0.62, 0), shoulder)
		_arms.append(shoulder)
	var head := SphereMesh.new()
	head.radius = 0.11
	head.height = 0.24
	_part(head, skin, Vector3(0, 1.66, -0.01))
	# hood over the back and top of the head, the face open toward -Z
	var cowl := SphereMesh.new()
	cowl.radius = 0.135
	cowl.height = 0.27
	_part(cowl, hood, Vector3(0, 1.67, 0.03))
	var cape := BoxMesh.new()
	cape.size = Vector3(0.44, 0.1, 0.3)
	_part(cape, hood, Vector3(0, 1.5, 0.02))
