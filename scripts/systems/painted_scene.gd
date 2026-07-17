extends Node3D
## Painted scene, Disco Elysium architecture: a 2D painted backdrop with
## REAL-TIME 3D CHARACTERS walking on top of it. A fixed, calibrated
## camera maps backdrop pixels to positions on an invisible ground plane,
## so characters foreshorten with distance exactly like the painting
## implies. Characters are CharacterRig instances — procedurally
## animated 3D, lit by point lights placed where the painting's fires
## are. Everything comes from data/scenes/<id>.json:
## {
##   "id", "backdrop", "spawn": [px, py],
##   "walk_polygon": [[px, py], ...],           (backdrop pixel coords)
##   "camera": {"pitch", "yaw", "fov", "distance"},
##   "lights": [{"px": [x, y], "height", "color", "energy", "range"}],
##   "player": {"palette": {"body": "#rrggbb", "head": "#rrggbb"}},
##   "npcs": [{"id", "name", "pos": [px, py], "palette": {...},
##             "dialogue", "portrait", "interact_radius"}]     (px radius)
## }

const SPEED := 2.6

@export var scene_id: String = ""

var runner: DialogueRunner = null
var nearby_npc: Dictionary = {}
var manifest: Dictionary = {}
var walk_polygon := PackedVector2Array()
var npcs: Array[Dictionary] = []
var input_enabled := true
var player: CharacterRig
var camera: Camera3D
var backdrop_size := Vector2(1536, 1024)

@onready var dialogue_ui: Control = $UI/DialogueUI
@onready var hud: Control = $UI/Hud


func _ready() -> void:
	manifest = Db.get_scene(scene_id)
	if manifest.is_empty():
		push_error("PaintedScene: no manifest for '%s'" % scene_id)
		return
	_build_camera()
	_build_backdrop()
	_build_lights()
	_build_player()
	_build_npcs()
	dialogue_ui.option_chosen.connect(_on_option_chosen)
	Store.state_changed.connect(func(_s: Dictionary) -> void: hud.refresh())
	hud.refresh()


## The painting is an unshaded quad glued to the camera's far plane,
## sized to exactly fill the frustum — so backdrop pixels and screen
## pixels stay in perfect correspondence while 3D characters render
## in front of it with correct depth.
func _build_backdrop() -> void:
	var texture: Texture2D = load(manifest["backdrop"])
	backdrop_size = texture.get_size()
	var quad := MeshInstance3D.new()
	var mesh := QuadMesh.new()
	var depth := 90.0
	var half_height := depth * tan(deg_to_rad(camera.fov / 2.0))
	var viewport_size: Vector2 = get_viewport().get_visible_rect().size
	var aspect := viewport_size.x / viewport_size.y
	mesh.size = Vector2(half_height * 2.0 * aspect, half_height * 2.0)
	var material := StandardMaterial3D.new()
	material.albedo_texture = texture
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mesh.material = material
	quad.mesh = mesh
	quad.position = Vector3(0, 0, -depth)
	camera.add_child(quad)
	for point: Array in manifest.get("walk_polygon", []):
		walk_polygon.append(Vector2(point[0], point[1]))


func _build_camera() -> void:
	var config: Dictionary = manifest.get("camera", {})
	var pitch := deg_to_rad(float(config.get("pitch", -42.0)))
	var yaw := deg_to_rad(float(config.get("yaw", 0.0)))
	var distance := float(config.get("distance", 26.0))
	camera = Camera3D.new()
	camera.fov = float(config.get("fov", 32.0))
	var offset := Vector3(0, 0, distance).rotated(Vector3.RIGHT, pitch).rotated(Vector3.UP, yaw)
	camera.position = offset
	add_child(camera)
	camera.look_at(Vector3.ZERO, Vector3.UP)
	camera.make_current()
	# The 3D layer renders over the backdrop; keep the world unlit-dark
	# so only the manifest lights sculpt the characters.
	var env := Environment.new()
	env.background_mode = Environment.BG_CLEAR_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.45, 0.48, 0.6)
	env.ambient_light_energy = 0.6
	camera.environment = env


func _build_lights() -> void:
	for light_data: Dictionary in manifest.get("lights", []):
		var light := OmniLight3D.new()
		var px: Array = light_data["px"]
		light.position = (
			px_to_world(Vector2(px[0], px[1])) + Vector3(0, float(light_data.get("height", 2.0)), 0)
		)
		light.light_color = Color(str(light_data.get("color", "#ffb060")))
		light.light_energy = float(light_data.get("energy", 4.0))
		light.omni_range = float(light_data.get("range", 8.0))
		add_child(light)


func _build_player() -> void:
	player = _make_character(manifest.get("player", {}).get("palette", {}))
	player.name = "Player"
	var spawn: Array = manifest["spawn"]
	player.position = px_to_world(Vector2(spawn[0], spawn[1]))


func _build_npcs() -> void:
	for npc_data: Dictionary in manifest.get("npcs", []):
		var rig := _make_character(npc_data.get("palette", {}))
		rig.name = "Npc_%s" % npc_data["id"]
		var pos: Array = npc_data["pos"]
		rig.position = px_to_world(Vector2(pos[0], pos[1]))
		var label := Label3D.new()
		label.text = str(npc_data.get("name", ""))
		label.position.y = 2.1
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.font_size = 40
		label.outline_size = 10
		rig.add_child(label)
		npcs.append({"data": npc_data, "rig": rig})


func _make_character(palette: Dictionary) -> CharacterRig:
	var rig := CharacterRig.new()
	rig.body_color = Color(str(palette.get("body", "#59636f")))
	rig.head_color = Color(str(palette.get("head", "#c8a284")))
	add_child(rig)
	return rig


## Map a backdrop pixel to the point on the ground plane (y=0) that the
## fixed camera sees at that screen position. This is the whole trick:
## the painting IS the screen, so pixel coords define world positions.
func px_to_world(px: Vector2) -> Vector3:
	var viewport_size: Vector2 = get_viewport().get_visible_rect().size
	var screen := px * (viewport_size / backdrop_size)
	var origin := camera.project_ray_origin(screen)
	var normal := camera.project_ray_normal(screen)
	if absf(normal.y) < 0.0001:
		return Vector3.ZERO
	var t := -origin.y / normal.y
	return origin + normal * t


func world_to_px(world: Vector3) -> Vector2:
	var viewport_size: Vector2 = get_viewport().get_visible_rect().size
	return camera.unproject_position(world) * (backdrop_size / viewport_size)


func _process(delta: float) -> void:
	if player == null:
		return
	_move_player(delta)
	for npc in npcs:
		npc["rig"].animate(delta, 0.0)
	_update_nearby_npc()


func _move_player(delta: float) -> void:
	var input_dir := Vector2.ZERO
	if input_enabled:
		input_dir = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	var speed := input_dir.length()
	if speed > 0.01:
		# Screen-space input: up moves toward the top of the painting.
		var direction := Vector3(input_dir.x, 0, input_dir.y).rotated(Vector3.UP, camera.rotation.y)
		var next := player.position + direction * SPEED * delta
		var next_px := world_to_px(next)
		if walk_polygon.is_empty() or Geometry2D.is_point_in_polygon(next_px, walk_polygon):
			player.position = next
		player.face_direction(direction, delta)
	player.animate(delta, speed)


func _update_nearby_npc() -> void:
	var player_px := world_to_px(player.position)
	var closest: Dictionary = {}
	var closest_dist := INF
	for npc in npcs:
		var radius := float(npc["data"].get("interact_radius", 150))
		var dist: float = player_px.distance_to(world_to_px(npc["rig"].position))
		if dist < radius and dist < closest_dist:
			closest = npc
			closest_dist = dist
	if closest != nearby_npc:
		nearby_npc = closest
		if nearby_npc.is_empty():
			hud.hide_prompt()
		else:
			hud.show_prompt("[E] Talk to %s" % nearby_npc["data"].get("name", "?"))


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("interact") and runner == null and not nearby_npc.is_empty():
		start_dialogue(nearby_npc)
	elif event.is_action_pressed("save_game"):
		SaveSystem.save_game(Store.get_state())
		hud.flash_message("Game saved")
	elif event.is_action_pressed("load_game"):
		var loaded := SaveSystem.load_game()
		if loaded.is_empty():
			hud.flash_message("No save found")
		elif Store.restore(loaded):
			hud.flash_message("Game loaded")


func start_dialogue(npc: Dictionary) -> void:
	var data: Dictionary = Db.get_dialogue(npc["data"].get("dialogue", ""))
	if data.is_empty():
		return
	var rig: CharacterRig = npc["rig"]
	rig.face_direction(player.position - rig.position, 1.0, 1.0)
	player.face_direction(rig.position - player.position, 1.0, 1.0)
	runner = DialogueRunner.new(data)
	runner.ended.connect(_on_dialogue_ended)
	runner.start()
	input_enabled = false
	_show_current_node(npc)


func _show_current_node(npc: Dictionary) -> void:
	var node := runner.current_node()
	var speaker: String = node.get("speaker", str(npc["data"].get("name", "")))
	var portrait: Texture2D = null
	var portrait_path: String = npc["data"].get("portrait", "")
	if not portrait_path.is_empty():
		portrait = load(portrait_path)
	dialogue_ui.show_node(
		speaker, node.get("text", ""), runner.visible_options(Store.get_state()), portrait
	)


func _on_option_chosen(option_index: int) -> void:
	if runner == null:
		return
	runner.choose(option_index, Store)
	if runner != null and runner.is_running() and not nearby_npc.is_empty():
		_show_current_node(nearby_npc)


func _on_dialogue_ended() -> void:
	runner = null
	dialogue_ui.hide()
	input_enabled = true
