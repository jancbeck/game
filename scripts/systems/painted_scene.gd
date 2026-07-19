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
##   "lights": [{"px": [x, y], "color", "energy", "range", "fire",
##               # placement — pick one:
##               "height",                    (ground fire: lift above ground)
##               "wall": true, "wall_height", (wall torch: read flame at height)
##               "world": [x, y, z]}],        (explicit 3D position)
##   "player": {"build"},                  (the convict GLB; palette unused)
##   "npcs": [{"id", "name", "pos": [px, py], "palette": {...}, "build",
##             "dialogue", "portrait", "interact_radius"}]     (px radius)
##   "occluders": [{"polygon": [[px, py], ...], "anchor": [px, py]}]
##                (bake-time input only: tools/bake_occluders.py cuts these
##                regions out of the backdrop offline; at runtime we load the
##                committed cards from art/occluders/<id>/, see _build_occluders)
## }
## "build" (default 1.0) scales a character's height/bulk for silhouette
## variety — e.g. 1.1 reads as burlier, 0.9 as slighter.

const SPEED := 2.6
## The reusable director loaded when travelling: same script + UI, its
## scene_id set at runtime to the exit's destination.
const WORLD_TSCN := "res://scenes/painted/painted_world.tscn"
const FADE_TIME := 0.35

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
@onready var journal: Control = $UI/JournalPanel

var _fires: Array[OmniLight3D] = []
var _flicker_time := 0.0
var _voice_player: AudioStreamPlayer
var _fade: ColorRect
var _cutscene_active := false


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
	_build_occluders()
	_build_audio()
	_build_fade()
	dialogue_ui.option_chosen.connect(_on_option_chosen)
	Store.state_changed.connect(_on_state_changed)
	hud.refresh()


func _on_state_changed(_state: Dictionary) -> void:
	hud.refresh()
	# Completing the jailer conversation can open an exit; keep the prompt live.
	_refresh_prompt()


## A full-screen black overlay on the UI layer that fades from opaque to
## clear on scene entry — the "transition" that travel arrives through.
func _build_fade() -> void:
	_fade = ColorRect.new()
	_fade.color = Color(0, 0, 0, 1)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	var ui := get_node("UI")
	ui.add_child(_fade)
	var tween := create_tween()
	tween.tween_property(_fade, "color:a", 0.0, FADE_TIME)


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
		light.position = _light_position(light_data, Vector2(px[0], px[1]))
		light.light_color = Color(str(light_data.get("color", "#ffb060")))
		light.light_energy = float(light_data.get("energy", 4.0))
		light.omni_range = float(light_data.get("range", 8.0))
		add_child(light)
		if light_data.get("fire", false):
			_fires.append(light)
			light.add_child(_make_fire_particles())
			var crackle := AudioStreamPlayer3D.new()
			crackle.stream = _looped_wav("res://art/audio/fire_crackle.wav")
			crackle.unit_size = 6.0
			crackle.autoplay = true
			light.add_child(crackle)


## Where a manifest light sits in 3D. Ground fires (braziers) are
## ground-projected with a small vertical lift, as before. Wall-mounted fires
## carry an authored height hint so they land AT the painted flame instead of
## being ground-projected far up the wall: "world":[x,y,z] for a fully explicit
## position, or "wall":true + "wall_height" to unproject the flame pixel onto a
## horizontal plane at that height (see docs/PIPELINE.md).
func _light_position(light_data: Dictionary, px: Vector2) -> Vector3:
	if light_data.has("world"):
		var w: Array = light_data["world"]
		return Vector3(w[0], w[1], w[2])
	if light_data.get("wall", false):
		return px_to_world_at_height(px, float(light_data.get("wall_height", 3.0)))
	return px_to_world(px) + Vector3(0, float(light_data.get("height", 2.0)), 0)


func _build_player() -> void:
	# The player is the convict: the rigged, animated Blender model
	# (scripts/world/convict_rig.gd). NPCs stay procedural CharacterRigs.
	# The manifest "build" scalar still applies; its palette does not —
	# the convict's colors are baked into the model from the sprite.
	player = ConvictRig.new()
	player.build = float(manifest.get("player", {}).get("build", 1.0))
	add_child(player)
	player.name = "Player"
	var spawn: Array = manifest["spawn"]
	player.position = px_to_world(Vector2(spawn[0], spawn[1]))


func _build_npcs() -> void:
	for npc_data: Dictionary in manifest.get("npcs", []):
		var rig := _make_character(npc_data.get("palette", {}), float(npc_data.get("build", 1.0)))
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


func _make_character(palette: Dictionary, build: float = 1.0) -> CharacterRig:
	var rig := CharacterRig.new()
	rig.body_color = Color(str(palette.get("body", "#59636f")))
	rig.head_color = Color(str(palette.get("head", "#c8a284")))
	rig.build = build
	add_child(rig)
	return rig


## Foreground occlusion — the "depth map" of this pipeline, authorable as
## text: each occluder is a polygon of backdrop pixels (a prop painted in
## the foreground) plus an anchor where it meets the ground. The manifest
## polygons are BAKE-TIME input: tools/bake_occluders.py cuts each region
## out of the painting offline (alpha-masked by the polygon) and commits
## trimmed RGBA cards plus a cards.json index under art/occluders/<scene>/.
## Here we load those pre-baked cards and mount each as a camera-facing
## quad at the anchor's TRUE 3D depth. Characters walking behind the anchor
## line are then genuinely occluded by the depth buffer — same effect as
## Disco Elysium's height maps, built from polygons instead of a painted
## depth pass. There is no runtime fallback: missing cards are an authoring
## error (re-run the baker), not something we paper over per-pixel.
func _build_occluders() -> void:
	if manifest.get("occluders", []).is_empty():
		return
	var cards_path := "res://art/occluders/%s/cards.json" % scene_id
	var data: Variant = null
	if FileAccess.file_exists(cards_path):
		data = JSON.parse_string(FileAccess.get_file_as_string(cards_path))
	if not data is Dictionary or not (data as Dictionary).get("cards") is Array:
		var msg := "PaintedScene: no usable occluder cards at '%s' — run tools/bake_occluders.py"
		push_error(msg % cards_path)
		return
	var cards: Array = data["cards"]
	for i in cards.size():
		var card: Dictionary = cards[i]
		var anchor_arr: Array = card["anchor"]
		var anchor_px := Vector2(anchor_arr[0], anchor_arr[1])
		var bounds_arr: Array = card["bounds"]
		var bounds := Rect2i(
			int(bounds_arr[0]), int(bounds_arr[1]), int(bounds_arr[2]), int(bounds_arr[3])
		)
		var anchor_world := px_to_world(anchor_px)
		var wpp := _world_per_backdrop_px(anchor_world)
		var quad := MeshInstance3D.new()
		quad.name = "OccluderCard_%d" % i
		var mesh := QuadMesh.new()
		mesh.size = Vector2(bounds.size.x * wpp, bounds.size.y * wpp)
		var material := StandardMaterial3D.new()
		material.albedo_texture = load(str(card["card"]))
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
		mesh.material = material
		quad.mesh = mesh
		quad.position = (
			anchor_world
			+ Vector3(
				(bounds.get_center().x - anchor_px.x) * wpp,
				(anchor_px.y - bounds.get_center().y) * wpp,
				0
			)
		)
		quad.basis = camera.global_transform.basis
		add_child(quad)


## World-units per backdrop pixel at a given world point's camera depth.
func _world_per_backdrop_px(at: Vector3) -> float:
	var depth: float = absf((camera.global_transform.affine_inverse() * at).z)
	var frustum_height := 2.0 * depth * tan(deg_to_rad(camera.fov / 2.0))
	return frustum_height / backdrop_size.y


func _make_fire_particles() -> GPUParticles3D:
	var particles := GPUParticles3D.new()
	var process := ParticleProcessMaterial.new()
	process.direction = Vector3(0, 1, 0)
	process.initial_velocity_min = 0.6
	process.initial_velocity_max = 1.4
	process.gravity = Vector3(0, 0.9, 0)
	process.scale_min = 0.04
	process.scale_max = 0.14
	process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	process.emission_sphere_radius = 0.18
	process.color_ramp = _fire_gradient()
	particles.process_material = process
	particles.amount = 28
	particles.lifetime = 0.9
	var mesh := QuadMesh.new()
	mesh.size = Vector2(0.12, 0.12)
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.vertex_color_use_as_albedo = true
	material.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mesh.material = material
	particles.draw_pass_1 = mesh
	particles.position.y = -0.6
	return particles


func _fire_gradient() -> GradientTexture1D:
	var gradient := Gradient.new()
	gradient.set_color(0, Color(1.0, 0.85, 0.4, 0.9))
	gradient.set_color(1, Color(0.9, 0.25, 0.05, 0.0))
	var texture := GradientTexture1D.new()
	texture.gradient = gradient
	return texture


func _build_audio() -> void:
	var ambience_path: String = manifest.get("ambience", "")
	if not ambience_path.is_empty():
		var ambience := AudioStreamPlayer.new()
		ambience.stream = _looped_wav(ambience_path)
		ambience.volume_db = -8.0
		ambience.autoplay = true
		add_child(ambience)
	_voice_player = AudioStreamPlayer.new()
	add_child(_voice_player)


static func _looped_wav(path: String) -> AudioStreamWAV:
	var stream: AudioStreamWAV = load(path)
	if stream:
		stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
		stream.loop_end = stream.data.size() / 2
	return stream


## Map a backdrop pixel to the point on the ground plane (y=0) that the
## fixed camera sees at that screen position. This is the whole trick:
## the painting IS the screen, so pixel coords define world positions.
func px_to_world(px: Vector2) -> Vector3:
	return px_to_world_at_height(px, 0.0)


## Unproject a backdrop pixel onto the horizontal plane at world height
## `plane_y`. `plane_y = 0` is the ground plane — the default mapping the whole
## illusion rests on. A positive height is how wall-mounted lights are placed
## AT the painted flame (the flame pixel, read on a plane at flame height)
## rather than ground-projected far up the wall.
func px_to_world_at_height(px: Vector2, plane_y: float) -> Vector3:
	var viewport_size: Vector2 = get_viewport().get_visible_rect().size
	var screen := px * (viewport_size / backdrop_size)
	var origin := camera.project_ray_origin(screen)
	var normal := camera.project_ray_normal(screen)
	if absf(normal.y) < 0.0001:
		return Vector3.ZERO
	var t := (plane_y - origin.y) / normal.y
	return origin + normal * t


func world_to_px(world: Vector3) -> Vector2:
	var viewport_size: Vector2 = get_viewport().get_visible_rect().size
	return camera.unproject_position(world) * (backdrop_size / viewport_size)


func _process(delta: float) -> void:
	if player == null:
		return
	# A running cutscene drives its own actors; suspend player control and the
	# idle-animation of NPCs so the timeline's movement is not fought each frame.
	if not _cutscene_active:
		_move_player(delta)
		for npc in npcs:
			npc["rig"].animate(delta, 0.0)
		_update_nearby_npc()
	_flicker_fires(delta)


func _flicker_fires(delta: float) -> void:
	_flicker_time += delta
	for i in _fires.size():
		var base := 6.0
		_fires[i].light_energy = (
			base
			* (
				1.0
				+ 0.18 * sin(_flicker_time * 9.0 + i * 2.1)
				+ 0.1 * sin(_flicker_time * 23.0 + i)
			)
		)


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
		_refresh_prompt()


## Decide what the interaction prompt shows: a nearby NPC to talk to takes
## priority; otherwise, if this scene has a currently-open exit, offer to
## travel; otherwise nothing.
func _refresh_prompt() -> void:
	if not nearby_npc.is_empty():
		hud.show_prompt("[E] Talk to %s" % nearby_npc["data"].get("name", "?"))
		return
	var scene_exit := available_exit()
	if scene_exit.is_empty():
		hud.hide_prompt()
	else:
		hud.show_prompt("[E] %s" % scene_exit.get("label", "Travel"))


## The first exit out of this scene whose requirements are currently met,
## or {} if the way onward is still locked. Data-driven: exits and their
## unlock conditions live in the scene manifest, evaluated by the reducer.
func available_exit() -> Dictionary:
	var exits: Array = Reducers.available_exits(Store.get_state(), manifest)
	return exits[0] if not exits.is_empty() else {}


## Travel to an exit's destination scene. Rebuilds the reusable painted-world
## director for the target scene id and swaps it in for this one — no
## hardcoded per-scene glue; the destination comes entirely from the exit.
func travel_to(scene_exit: Dictionary) -> Node:
	var target: String = scene_exit.get("to", "")
	if target.is_empty() or not Db.scenes.has(target):
		push_error("PaintedScene: exit to unknown scene '%s'" % target)
		return null
	var next: Node = (load(WORLD_TSCN) as PackedScene).instantiate()
	next.scene_id = target
	var tree := get_tree()
	tree.root.add_child(next)
	tree.current_scene = next
	queue_free()
	return next


func _unhandled_input(event: InputEvent) -> void:
	# The journal can be opened whenever no dialogue is running, and closed
	# while open; it pauses world movement like dialogue does.
	if event.is_action_pressed("toggle_journal") and runner == null:
		toggle_journal()
		return
	if journal.is_open():
		return
	if event.is_action_pressed("interact") and runner == null:
		if not nearby_npc.is_empty():
			start_dialogue(nearby_npc)
		else:
			var scene_exit := available_exit()
			if not scene_exit.is_empty():
				travel_to(scene_exit)
	elif event.is_action_pressed("save_game"):
		SaveSystem.save_game(Store.get_state())
		hud.flash_message("Game saved")
	elif event.is_action_pressed("load_game"):
		var loaded := SaveSystem.load_game()
		if loaded.is_empty():
			hud.flash_message("No save found")
		elif Store.restore(loaded):
			hud.flash_message("Game loaded")


func toggle_journal() -> void:
	journal.toggle()
	input_enabled = not journal.is_open()


func start_dialogue(npc: Dictionary) -> void:
	var data: Dictionary = Db.get_dialogue(npc["data"].get("dialogue", ""))
	if data.is_empty():
		return
	var rig: CharacterRig = npc["rig"]
	rig.face_direction(player.position - rig.position, 1.0, 1.0)
	player.face_direction(rig.position - player.position, 1.0, 1.0)
	# Both parties lean into the conversation (a gesture pose, not a rig).
	rig.set_speaking(true)
	player.set_speaking(true)
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
	var voice_path: String = node.get("voice", "")
	if not voice_path.is_empty() and ResourceLoader.exists(voice_path):
		_voice_player.stream = load(voice_path)
		_voice_player.play()
	elif _voice_player.playing:
		_voice_player.stop()
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
	player.set_speaking(false)
	for npc in npcs:
		npc["rig"].set_speaking(false)
	# The conversation may have unlocked the way onward.
	_refresh_prompt()


## Play a scripted set-piece: an ordered timeline (data/cutscenes/<id>.json)
## that walks actors, shows narration lines, and applies store effects with no
## player input. This is the ONLY glue — the CutsceneRunner sequences and
## applies store effects; here we perform the visual steps. Awaits until the
## timeline finishes, then restores player control.
func play_cutscene(cutscene_id: String) -> void:
	var data := Db.get_cutscene(cutscene_id)
	if data.is_empty():
		push_error("PaintedScene: no cutscene '%s'" % cutscene_id)
		return
	var cut := CutsceneRunner.new(data)
	_cutscene_active = true
	input_enabled = false
	nearby_npc = {}
	hud.hide_prompt()
	cut.start()
	while cut.is_running():
		var step: Dictionary = cut.current_step()
		if not cut.apply(step, Store):
			await _perform_cutscene_step(step)
		cut.advance()
	dialogue_ui.hide()
	_cutscene_active = false
	input_enabled = true
	_refresh_prompt()


## Perform one visual (non-store) cutscene step and return when it is done.
func _perform_cutscene_step(step: Dictionary) -> void:
	match str(step.get("type", "")):
		"wait":
			await _wait_seconds(float(step.get("seconds", 1.0)))
		"walk":
			await _walk_actor(step)
		"line":
			await _show_cutscene_line(step)


## The rig a cutscene step addresses: "player" or an NPC id from this scene.
func _actor(actor_id: String) -> CharacterRig:
	if actor_id == "player":
		return player
	for npc in npcs:
		if str(npc["data"].get("id", "")) == actor_id:
			return npc["rig"]
	return null


## Walk an actor to a backdrop-pixel target, animating the procedural rig.
## Bounded by a wall-clock guard so a bad target can never hang the timeline.
func _walk_actor(step: Dictionary) -> void:
	var actor := _actor(str(step.get("actor", "player")))
	var to: Array = step.get("to", [])
	if actor == null or to.size() < 2:
		return
	var target := px_to_world(Vector2(to[0], to[1]))
	var speed := float(step.get("speed", SPEED))
	var guard := 0.0
	while actor.position.distance_to(target) > 0.08 and guard < 10.0:
		var delta := get_process_delta_time()
		guard += delta
		var direction := target - actor.position
		direction.y = 0.0
		actor.position = actor.position.move_toward(target, speed * delta)
		actor.face_direction(direction, delta)
		actor.animate(delta, 1.0)
		await get_tree().process_frame
	actor.position = target
	var face: Array = step.get("face", [])
	if face.size() >= 2:
		actor.face_direction(px_to_world(Vector2(face[0], face[1])) - actor.position, 1.0, 1.0)


## Show a narration/scripted line (no options) and hold it for `seconds`.
func _show_cutscene_line(step: Dictionary) -> void:
	var portrait: Texture2D = null
	var portrait_path := str(step.get("portrait", ""))
	if not portrait_path.is_empty() and ResourceLoader.exists(portrait_path):
		portrait = load(portrait_path)
	var no_options: Array[Dictionary] = []
	dialogue_ui.show_node(
		str(step.get("speaker", "")), str(step.get("text", "")), no_options, portrait
	)
	await _wait_seconds(float(step.get("seconds", 2.0)))


func _wait_seconds(seconds: float) -> void:
	if seconds <= 0.0:
		return
	await get_tree().create_timer(seconds).timeout
