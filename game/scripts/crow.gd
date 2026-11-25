## One crow: idles on a perch the way scene/anim_crows.py's perched crows do (head jerks and holds,
## pecks on the ground, short hops that turn it, wing shuffles, tail flicks), and flies between
## perches on a curved path, banking into turns, flapping on take-off and landing and gliding
## between.
##
## The model (crow.glb) faces +Z with its feet at the origin; body, head, tail, wing_l and wing_r
## are found by name, and turn about their own pivots.
extends Node3D

signal took_off(crow)
signal landed(crow)

const HOP_TIME := 0.34
const GRAVITY := 9.81
const MAX_BANK := deg_to_rad(35.0)

var rng := RandomNumberGenerator.new()
var perch: Dictionary          # {id, pos: Vector3, yaw (rad)}
var flying := false
var spread := deg_to_rad(80.0) # how far the wings open in flight

var _parts := {}               # name -> [node, rest Transform3D]
var _yaw := 0.0                # current heading on the perch (rad)
var _t := 0.0
var _head_from := Vector2.ZERO # yaw, pitch in degrees
var _head_to := Vector2.ZERO
var _head_t0 := -1.0
var _next_head := 0.0
var _hop_t0 := -10.0
var _hop_turn := 0.0
var _next_hop := 0.0
var _shuffle_t0 := -10.0
var _shuffle_amp := 0.0
var _next_shuffle := 0.0
var _flick_t0 := -10.0
var _flick_amp := 0.0
var _next_flick := 0.0
var _peck := []                 # pending [time, pitch] keys

var _curve: Array = []         # 4 Bezier points
var _fly_t0 := 0.0
var _fly_dur := 1.0
var _beat_seed := 0


func setup(model: Node3D, seed: int, at: Dictionary) -> void:
	rng.seed = seed
	_beat_seed = seed
	add_child(model)
	_dress(model)
	for key in ["body", "head", "tail", "wing_l", "wing_r"]:
		var n := _find(model, key)
		if n:
			_parts[key] = [n, n.transform]
	place(at)
	_next_head = rng.randf_range(0.4, 3.5)
	_next_hop = rng.randf_range(2.0, 11.0)
	_next_shuffle = rng.randf_range(1.0, 9.0)
	_next_flick = rng.randf_range(0.5, 4.5)


## Dark glossy feathers with a wet sheen: near-black with a blue-violet cast, a clear coat that
## picks up the sky and the fires, and a rim from lights behind the bird. The albedo sits a little
## above real crow black because the grade's lift (0.97) crushes anything darker to pure black.
static var _feathers: StandardMaterial3D
static var _beak: StandardMaterial3D


static func _dress(model: Node) -> void:
	if _feathers == null:
		_feathers = StandardMaterial3D.new()
		_feathers.albedo_color = Color(0.075, 0.077, 0.092)
		_feathers.roughness = 0.38
		_feathers.metallic_specular = 0.6
		_feathers.clearcoat_enabled = true
		_feathers.clearcoat = 1.0
		_feathers.clearcoat_roughness = 0.15
		_feathers.rim_enabled = true
		_feathers.rim = 0.7
		_feathers.rim_tint = 0.2
		_beak = StandardMaterial3D.new()
		_beak.albedo_color = Color(0.03, 0.03, 0.03)
		_beak.roughness = 0.3
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		var is_beak := String(mi.name).to_lower().contains("beak") or String(mi.name).to_lower().contains("bill")
		mi.material_override = _beak if is_beak else _feathers


## The shallowest node whose name is the key, or contains it (wing_l also matches "left wing").
static func _find(root: Node, key: String) -> Node3D:
	var names: Array = {"wing_l": ["wing_l", "wingl", "left_wing", "wing_left", "wing.l"],
		"wing_r": ["wing_r", "wingr", "right_wing", "wing_right", "wing.r"]}.get(key, [key])
	var queue: Array[Node] = [root]
	while not queue.is_empty():
		var n: Node = queue.pop_front()
		var low := String(n.name).to_lower().replace(" ", "_")
		if n is Node3D and n != root and not low.ends_with("_mesh"):
			for k in names:
				if low == k or low.begins_with(k):
					return n
		queue.append_array(n.get_children())
	return null


func place(at: Dictionary) -> void:
	perch = at
	_yaw = at.yaw
	flying = false
	global_position = at.pos
	rotation = Vector3(0, _yaw, 0)


func on_ground() -> bool:
	return perch.pos.y < 0.1


# ---------- perched ----------

func _idle(t: float) -> void:
	if t >= _next_head:
		_head_from = _head_angles(t)
		_head_t0 = t
		if rng.randf() < 0.25:
			_head_to = Vector2(0.0, rng.randf_range(-4, 6))
		else:
			_head_to = Vector2(rng.randf_range(-55, 55), rng.randf_range(-8, 14))
		if on_ground() and rng.randf() < 0.3:
			_peck = [[t + 0.25, 48.0], [t + 0.55, 5.0]]
		_next_head = t + rng.randf_range(0.4, 3.5) + (0.6 if not _peck.is_empty() else 0.0)
	if not _peck.is_empty() and t >= _peck[0][0]:
		_head_from = _head_angles(t)
		_head_t0 = t
		_head_to = Vector2(_head_to.x, _peck[0][1])
		_peck.pop_front()
	if t >= _next_hop:
		_hop_t0 = t
		_hop_turn = [0.0, 1.0, -1.0][rng.randi_range(0, 2)] * rng.randf_range(25, 150)
		_next_hop = t + maxf(5.0, -11.0 * log(1.0 - rng.randf()))
	if t >= _next_shuffle:
		_shuffle_t0 = t
		_shuffle_amp = rng.randf_range(14, 30)
		_next_shuffle = t + maxf(3.0, -9.0 * log(1.0 - rng.randf()))
	if t >= _next_flick:
		_flick_t0 = t
		_flick_amp = rng.randf_range(8, 18)
		_next_flick = t + maxf(1.2, -4.5 * log(1.0 - rng.randf()))

	var z := 0.0
	var lift := 0.0
	var turn := 0.0
	var u := (t - _hop_t0) / HOP_TIME
	if u >= 0.0 and u < 1.0:
		turn = _hop_turn * _smooth(u * 1.2)
		z = 0.07 * sin(PI * u)
		lift = 30.0 * sin(PI * u)
	elif u >= 1.0 and _hop_turn != 0.0:
		_yaw += deg_to_rad(_hop_turn)
		_hop_turn = 0.0
	global_position = perch.pos + Vector3(0, z, 0)
	rotation = Vector3(0, _yaw + deg_to_rad(turn), 0)

	var h := _head_angles(t)
	_pose("head", Basis.from_euler(Vector3(deg_to_rad(h.y), deg_to_rad(h.x), 0)))
	var env := _pulse(t, _shuffle_t0, 0.55)
	var flap := maxf(lift, _shuffle_amp * env)
	for side in [["wing_r", 1.0], ["wing_l", -1.0]]:
		var sx: float = side[1]
		# Blender (x, y, z) rotation of anim_crows.py in Godot axes: (x, -z, y)
		_pose(side[0], Basis.from_euler(Vector3(deg_to_rad(0.3 * flap), deg_to_rad(-sx * flap), deg_to_rad(sx * 0.5 * flap))))
	_scale("body", 1.0 + 0.10 * env)
	var fl := _pulse(t, _flick_t0, 0.28)
	_pose("tail", Basis.from_euler(Vector3(deg_to_rad(-(_flick_amp * fl + 0.3 * flap)), 0, 0)))


func _head_angles(t: float) -> Vector2:
	if _head_t0 < 0.0:
		return Vector2.ZERO
	return _head_from.lerp(_head_to, _smooth((t - _head_t0) / 0.13))


static func _smooth(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	return x * x * (3.0 - 2.0 * x)


static func _pulse(t: float, t0: float, dur: float) -> float:
	var u := (t - t0) / dur
	return sin(PI * u) if u >= 0.0 and u < 1.0 else 0.0


func _pose(part: String, rot: Basis) -> void:
	if _parts.has(part):
		var rest: Transform3D = _parts[part][1]
		_parts[part][0].transform = Transform3D(rest.basis * rot, rest.origin)


func _scale(part: String, f: float) -> void:
	if _parts.has(part):
		var rest: Transform3D = _parts[part][1]
		_parts[part][0].transform = Transform3D(rest.basis.scaled_local(Vector3.ONE * f), rest.origin)


# ---------- flight ----------

## Take off toward a perch on two Bezier arcs like anim_crows.Crosser: up and out, over, down.
func fly_to(target: Dictionary, t: float) -> void:
	var a: Vector3 = perch.pos
	var b: Vector3 = target.pos
	var d := b - a
	d.y = 0.0
	var L := maxf(d.length(), 0.5)
	d = d / L
	var side := Vector3(-d.z, 0, d.x) * (1.0 if rng.randf() < 0.5 else -1.0)
	var up := Vector3.UP
	var lift := 0.19
	var rise := clampf(L * 0.25, 1.2, 3.0)
	_curve = [a + up * lift, a + up * (lift + rise) + d * 0.25 * L + side * 0.18 * L,
		b + up * (lift + rise + maxf(0.0, a.y - b.y) * 0.2) - d * 0.30 * L + side * 0.18 * L, b + up * lift]
	_fly_t0 = t
	_fly_dur = clampf(L / 6.5 + 1.2, 1.6, 6.0)
	perch = target
	flying = true
	took_off.emit(self)


func _bez(s: float) -> Vector3:
	var u := 1.0 - s
	return _curve[0] * u * u * u + _curve[1] * 3.0 * u * u * s + _curve[2] * 3.0 * u * s * s + _curve[3] * s * s * s


func _bez_d(s: float) -> Vector3:
	var u := 1.0 - s
	return (_curve[1] - _curve[0]) * 3.0 * u * u + (_curve[2] - _curve[1]) * 6.0 * u * s + (_curve[3] - _curve[2]) * 3.0 * s * s


static func _ease(u: float) -> float:
	u = clampf(u, 0.0, 1.0)
	return 0.5 * (u + u * u * (3.0 - 2.0 * u))


func _path_at(t: float) -> Vector3:
	return _bez(_ease((t - _fly_t0) / _fly_dur))


func _fly(t: float) -> void:
	var u := (t - _fly_t0) / _fly_dur
	if u >= 1.0:
		var arrive := _bez_d(1.0)
		place({id = perch.id, pos = perch.pos, yaw = atan2(arrive.x, arrive.z)})
		_hop_t0 = t - 0.1          # settles with a little hop
		_hop_turn = rad_to_deg(wrapf(perch.get("home_yaw", _yaw) - _yaw, -PI, PI)) * 0.5
		landed.emit(self)
		return
	var h := 1.0 / 60.0
	var p0 := _path_at(t - h)
	var p1 := _path_at(t)
	var p2 := _path_at(t + h)
	var vel := (p2 - p0) / (2.0 * h)
	var acc := (p0 - 2.0 * p1 + p2) / (h * h)
	var tangent := _bez_d(_ease(u))
	var run := Vector2(tangent.x, tangent.z).length()
	var climb := clampf(rad_to_deg(atan2(tangent.y, run)), -25.0, 30.0)
	var flare := _smooth((u - 0.78) / 0.2)
	var nose_up := climb * (1.0 - flare) + 25.0 * flare
	var fwd := Vector3(vel.x, 0, vel.z).normalized() if Vector2(vel.x, vel.z).length() > 0.01 else global_basis.z
	# bank into the turn: the body's up leans toward the lateral acceleration
	var lat := Vector3(acc.x, 0, acc.z)
	lat -= fwd * lat.dot(fwd)
	if lat.length() > GRAVITY * tan(MAX_BANK):
		lat = lat.normalized() * GRAVITY * tan(MAX_BANK)
	var upv := (Vector3.UP * GRAVITY + lat).normalized()
	var z := fwd
	var y := (upv - z * upv.dot(z)).normalized()
	var x := y.cross(z)
	var basis := Basis(x, y, z) * Basis(Vector3.RIGHT, deg_to_rad(-nose_up))
	var beat: float
	var bob := 0.0
	if u < 0.35:
		beat = _wingbeat(t, 4.6)
		bob = 0.03 * cos(TAU * 4.6 * t)
	elif u < 0.72:
		beat = 0.42 + 0.05 * sin(t * 3.0)
	else:
		beat = _wingbeat(t, 4.2) * (1.0 - 0.5 * flare)
	global_transform = Transform3D(basis, p1 + Vector3(0, bob, 0))
	# beat 0 = top of the up-stroke, 1 = bottom of the down-stroke
	var flap := deg_to_rad(lerpf(55.0, -35.0, beat))
	for side in [["wing_r", 1.0], ["wing_l", -1.0]]:
		var sx: float = side[1]
		_pose(side[0], Basis(Vector3.BACK, sx * flap) * Basis(Vector3.UP, -sx * spread))
	_pose("head", Basis.IDENTITY)
	_pose("tail", Basis.from_euler(Vector3(deg_to_rad(-6.0 * flare), 0, 0)))
	_scale("body", 1.0)


func _wingbeat(t: float, freq: float) -> float:
	var ph := freq * t + 0.15 * sin(t * 0.7 + _beat_seed)
	return 0.5 - 0.5 * cos(TAU * ph)


func update(t: float) -> void:
	_t = t
	if flying:
		_fly(t)
	else:
		_idle(t)
