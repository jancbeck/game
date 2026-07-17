extends Node2D
## Generic player for painted scenes — the Disco Elysium-style pipeline.
## A scene is DATA (data/scenes/<id>.json): a painted backdrop image,
## a walkable polygon in backdrop pixel coordinates, a spawn point, and
## NPC placements. This node builds the whole playable scene from that
## manifest at runtime; adding a location to the game means adding a
## painting and a JSON file, not engineering.
##
## Manifest format:
## {
##   "id": "prison_yard",
##   "backdrop": "res://art/scenes/prison_yard.png",
##   "spawn": [x, y],
##   "walk_polygon": [[x, y], ...],
##   "player": {"sprite": "res://art/sprites/convict.png", "scale": 0.5},
##   "npcs": [{"id", "name", "pos": [x, y], "sprite", "scale",
##             "dialogue", "interact_radius"}]
## }

const SPEED := 260.0

@export var scene_id: String = ""

var runner: DialogueRunner = null
var nearby_npc: Dictionary = {}
var manifest: Dictionary = {}
var walk_polygon := PackedVector2Array()
var npcs: Array[Dictionary] = []
var input_enabled := true
var player: Sprite2D
var camera: Camera2D

@onready var dialogue_ui: Control = $UI/DialogueUI
@onready var hud: Control = $UI/Hud

var _walk_phase := 0.0


func _ready() -> void:
	manifest = Db.get_scene(scene_id)
	if manifest.is_empty():
		push_error("PaintedScene: no manifest for '%s'" % scene_id)
		return
	y_sort_enabled = true
	_build_backdrop()
	_build_player()
	_build_npcs()
	_build_camera()
	dialogue_ui.option_chosen.connect(_on_option_chosen)
	Store.state_changed.connect(func(_s: Dictionary) -> void: hud.refresh())
	hud.refresh()


func _build_backdrop() -> void:
	var backdrop := Sprite2D.new()
	backdrop.name = "Backdrop"
	backdrop.texture = load(manifest["backdrop"])
	backdrop.centered = false
	backdrop.z_index = -100
	add_child(backdrop)
	for point: Array in manifest.get("walk_polygon", []):
		walk_polygon.append(Vector2(point[0], point[1]))


func _build_player() -> void:
	player = _make_character(
		manifest.get("player", {}).get("sprite", ""),
		Vector2(manifest["spawn"][0], manifest["spawn"][1]),
		float(manifest.get("player", {}).get("scale", 1.0))
	)
	player.name = "Player"


func _build_npcs() -> void:
	for npc_data: Dictionary in manifest.get("npcs", []):
		var sprite := _make_character(
			npc_data.get("sprite", ""),
			Vector2(npc_data["pos"][0], npc_data["pos"][1]),
			float(npc_data.get("scale", 1.0))
		)
		sprite.name = "Npc_%s" % npc_data["id"]
		var label := Label.new()
		label.text = npc_data.get("name", "")
		label.position = Vector2(-80, -sprite.texture.get_height() * sprite.scale.y - 28)
		label.custom_minimum_size = Vector2(160, 0)
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		sprite.add_child(label)
		npcs.append({"data": npc_data, "sprite": sprite})


## Characters have their origin at their FEET so Y-sort against other
## scene elements works naturally.
func _make_character(sprite_path: String, at: Vector2, char_scale: float) -> Sprite2D:
	var sprite := Sprite2D.new()
	sprite.texture = load(sprite_path)
	sprite.offset = Vector2(0, -sprite.texture.get_height() / 2.0)
	sprite.scale = Vector2(char_scale, char_scale)
	sprite.position = at
	sprite.y_sort_enabled = true
	add_child(sprite)
	return sprite


func _build_camera() -> void:
	camera = Camera2D.new()
	var tex: Texture2D = load(manifest["backdrop"])
	camera.limit_left = 0
	camera.limit_top = 0
	camera.limit_right = tex.get_width()
	camera.limit_bottom = tex.get_height()
	camera.position_smoothing_enabled = true
	player.add_child(camera)
	camera.make_current()


func _process(delta: float) -> void:
	if player == null:
		return
	_move_player(delta)
	_update_nearby_npc()


func _move_player(delta: float) -> void:
	var direction := Vector2.ZERO
	if input_enabled:
		direction = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	if direction.length() > 0.01:
		var next := player.position + direction * SPEED * delta
		if walk_polygon.is_empty() or Geometry2D.is_point_in_polygon(next, walk_polygon):
			player.position = next
		# Procedural bob, and face the way we walk.
		_walk_phase += delta * 10.0
		player.offset.y = -player.texture.get_height() / 2.0 - absf(sin(_walk_phase)) * 6.0
		if absf(direction.x) > 0.01:
			player.flip_h = direction.x < 0
	else:
		_walk_phase = 0.0
		player.offset.y = -player.texture.get_height() / 2.0


func _update_nearby_npc() -> void:
	var closest: Dictionary = {}
	var closest_dist := INF
	for npc in npcs:
		var radius := float(npc["data"].get("interact_radius", 140))
		var dist: float = player.position.distance_to(npc["sprite"].position)
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
	var npc_sprite: Sprite2D = npc["sprite"]
	npc_sprite.flip_h = player.position.x < npc_sprite.position.x
	runner = DialogueRunner.new(data)
	runner.ended.connect(_on_dialogue_ended)
	runner.start()
	input_enabled = false
	_show_current_node(str(npc["data"].get("name", "")))


func _show_current_node(speaker_fallback: String) -> void:
	var node := runner.current_node()
	var speaker: String = node.get("speaker", speaker_fallback)
	dialogue_ui.show_node(speaker, node.get("text", ""), runner.visible_options(Store.get_state()))


func _on_option_chosen(option_index: int) -> void:
	if runner == null:
		return
	runner.choose(option_index, Store)
	if runner != null and runner.is_running():
		var fallback: String = (
			str(nearby_npc["data"].get("name", "")) if not nearby_npc.is_empty() else ""
		)
		_show_current_node(fallback)


func _on_dialogue_ended() -> void:
	runner = null
	dialogue_ui.hide()
	input_enabled = true
