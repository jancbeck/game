class_name CharacterRig
extends Node3D
## A fully code-built, fully code-animated 3D character: torso, head,
## two arms, two legs — no skeletal rigs, no imported models, no
## retargeting. Walk cycle, idle breathing, and facing are procedural.
## Palette comes from data so characters match the painted scenes.

var body_color := Color(0.35, 0.4, 0.5)
var head_color := Color(0.78, 0.62, 0.5)
## Per-character silhouette scalar (from the manifest): 1.0 is the baseline,
## >1 taller/burlier, <1 slighter. Set before the node enters the tree.
var build := 1.0

var _root: Node3D
var _torso: MeshInstance3D
var _head: MeshInstance3D
var _arm_l: Node3D
var _arm_r: Node3D
var _leg_l: Node3D
var _leg_r: Node3D
var _phase := 0.0
var _idle_time := 0.0
var _speaking := false


func _ready() -> void:
	_build()


func _build() -> void:
	_root = Node3D.new()
	add_child(_root)
	var body_mat := StandardMaterial3D.new()
	body_mat.albedo_color = body_color
	body_mat.roughness = 0.9
	var head_mat := StandardMaterial3D.new()
	head_mat.albedo_color = head_color
	head_mat.roughness = 0.8

	# Proportions: taller than wide with a modestly-sized head (a stubby,
	# big-headed silhouette reads as gray-box). `build` scales height directly
	# and bulk more gently, so variety stays believable.
	var tall := build
	var bulk := 1.0 + (build - 1.0) * 0.6
	_torso = _capsule(0.2 * bulk, 0.82 * tall, body_mat)
	_torso.position.y = 1.18 * tall
	_root.add_child(_torso)
	_head = _capsule(0.115 * bulk, 0.26 * tall, head_mat)
	_head.position.y = 1.74 * tall
	_root.add_child(_head)
	_arm_l = _limb(0.06 * bulk, 0.66 * tall, body_mat, Vector3(-0.28 * bulk, 1.5 * tall, 0))
	_arm_r = _limb(0.06 * bulk, 0.66 * tall, body_mat, Vector3(0.28 * bulk, 1.5 * tall, 0))
	_leg_l = _limb(0.085 * bulk, 0.86 * tall, body_mat, Vector3(-0.12 * bulk, 0.9 * tall, 0))
	_leg_r = _limb(0.085 * bulk, 0.86 * tall, body_mat, Vector3(0.12 * bulk, 0.9 * tall, 0))
	# Soft contact-shadow blob so characters sit ON the painting.
	var blob := MeshInstance3D.new()
	var blob_mesh := PlaneMesh.new()
	blob_mesh.size = Vector2(0.9, 0.9)
	var blob_mat := StandardMaterial3D.new()
	blob_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	blob_mat.albedo_color = Color(0, 0, 0, 0.45)
	blob_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	blob_mesh.material = blob_mat
	blob.mesh = blob_mesh
	blob.position.y = 0.02
	add_child(blob)


func _capsule(radius: float, height: float, mat: Material) -> MeshInstance3D:
	var mesh_instance := MeshInstance3D.new()
	var capsule := CapsuleMesh.new()
	capsule.radius = radius
	capsule.height = height + radius * 2.0
	mesh_instance.mesh = capsule
	mesh_instance.material_override = mat
	return mesh_instance


## A limb pivots at its TOP (shoulder/hip) so swinging looks natural.
func _limb(radius: float, length: float, mat: Material, at: Vector3) -> Node3D:
	var pivot := Node3D.new()
	pivot.position = at
	var mesh_instance := _capsule(radius, length, mat)
	mesh_instance.position.y = -length / 2.0
	pivot.add_child(mesh_instance)
	_root.add_child(pivot)
	return pivot


func set_palette(body: Color, head: Color) -> void:
	body_color = body
	head_color = head
	if _root:
		_root.queue_free()
		_build()


## drive with speed in [0..1]; 0 = idle
func animate(delta: float, speed: float) -> void:
	_idle_time += delta
	if speed > 0.05:
		_phase += delta * 9.0 * maxf(speed, 0.4)
		var swing := sin(_phase) * 0.7 * speed
		_arm_l.rotation.x = swing
		_arm_r.rotation.x = -swing
		_leg_l.rotation.x = -swing
		_leg_r.rotation.x = swing
		_root.position.y = absf(sin(_phase)) * 0.05
		_root.rotation.x = 0.06 * speed
		_root.rotation.z = lerp_angle(_root.rotation.z, 0.0, delta * 10.0)
	else:
		_phase = 0.0
		var settle := 10.0 * delta
		if _speaking:
			_animate_speaking(settle)
		else:
			_animate_idle(settle)
		# Breathing keeps the figure alive in either idle mode.
		_torso.scale.y = 1.0 + sin(_idle_time * 2.1) * 0.012


func _animate_idle(settle: float) -> void:
	_arm_l.rotation.x = lerpf(_arm_l.rotation.x, sin(_idle_time * 1.3) * 0.04, settle)
	_arm_r.rotation.x = lerpf(_arm_r.rotation.x, -sin(_idle_time * 1.3) * 0.04, settle)
	_leg_l.rotation.x = lerpf(_leg_l.rotation.x, 0.0, settle)
	_leg_r.rotation.x = lerpf(_leg_r.rotation.x, 0.0, settle)
	_root.position.y = lerpf(_root.position.y, 0.0, settle)
	_root.rotation.x = lerpf(_root.rotation.x, 0.0, settle)
	# A slow weight shift from foot to foot — a subtle sway, not a march.
	_root.rotation.z = lerpf(_root.rotation.z, sin(_idle_time * 0.9) * 0.035, settle)
	_head.rotation.y = sin(_idle_time * 0.5) * 0.2


## Leaning-in conversation pose: the torso tips forward, the right hand lifts
## and makes small gestures, and the sway settles square.
func _animate_speaking(settle: float) -> void:
	var gesture := sin(_idle_time * 3.1)
	_root.rotation.x = lerpf(_root.rotation.x, 0.09, settle)
	_root.rotation.z = lerpf(_root.rotation.z, 0.0, settle)
	_root.position.y = lerpf(_root.position.y, 0.0, settle)
	_arm_r.rotation.x = lerpf(_arm_r.rotation.x, -0.55 - gesture * 0.22, settle)
	_arm_l.rotation.x = lerpf(_arm_l.rotation.x, 0.12, settle)
	_leg_l.rotation.x = lerpf(_leg_l.rotation.x, 0.0, settle)
	_leg_r.rotation.x = lerpf(_leg_r.rotation.x, 0.0, settle)
	_head.rotation.y = lerpf(_head.rotation.y, gesture * 0.06, settle)


## Toggle the leaning-in gesture pose used during dialogue.
func set_speaking(on: bool) -> void:
	_speaking = on


## Turn (smoothly) to face a world-space direction on the ground plane.
func face_direction(direction: Vector3, delta: float, turn_speed: float = 12.0) -> void:
	var flat := Vector3(direction.x, 0, direction.z)
	if flat.length() > 0.01:
		var target_yaw := atan2(-flat.x, -flat.z)
		rotation.y = lerp_angle(rotation.y, target_yaw, turn_speed * delta)
