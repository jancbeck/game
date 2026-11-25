## Courtyard slice: the pre-rendered frame as live layers, with a walking figure, crows, rain,
## flipbooks, hotspots, exits and portals, under a camera that zooms.
##
## All data comes from the scene.json named in config.json (see scene_data.gd). The parts:
##   view.gd          SubViewport at window resolution + Blender's view transform (3D LUT)
##   camera_rig.gd    zoom 0.5 (intro) / 1 / 2 (interaction), screen px <-> frame px
##   compositor.gd    base + light groups x flicker curves from the main, wide and tile sources;
##                    depth, ids, rain ripples and splashes, hover outline
##   lights.gd        real-time lights that follow their group
##   flipbooks.gd     flames, smoke, mist
##   rain.gd          rain drops as GPU particles, splashes where they land
##   crows.gd         perched and flying crows
##   navigation.gd    navmesh from walk.glb, surfaces, links, exits, portals
##   portals.gd       doors the figure goes through
##   interaction.gd   hover, clicks, outline, interactions, exits
##   audio.gd         rain bed, fire, footsteps, clicks, hotspot and door sounds
##   npc.gd           people to talk to (data/npcs/*.json): figure, talking portrait, voice clips
##   story.gd         the Ink story: conversations, look texts, quest variables
##   dialogue.gd      plays the story in the dialogue column
##   session.gd       location, satchel, quest flags, save and load, change of location
##   pad.gd           the Xbox pad: stick walking, selection, buttons
##   inventory_ui.gd  the satchel strip; quest_panel.gd: quest state under F1
##   skills.gd, journal.gd  the six skills and the checks against them, the journal's tasks
##   sheet_ui.gd      the character sheet (C) and the journal (J)
##   menu_ui.gd       the title screen, the pause menu (Esc), new game, load and save, settings
##   chapter_ui.gd    the card and the page of the player's choices when the story ends a chapter
##   settings.gd, saves.gd, archetypes.gd   the player's settings, the save slots, the builds of a new game
##   perf.gd          F3 frame-time overlay; logs/perf.csv with 5 s windows and hitches
extends Node

const SceneData := preload("res://scripts/scene_data.gd")
const Locations := preload("res://scripts/locations.gd")
const Actions := preload("res://scripts/actions.gd")
const Cursor := preload("res://scripts/cursor.gd")
const Session := preload("res://scripts/session.gd")
const Story := preload("res://scripts/story.gd")
const Settings := preload("res://scripts/settings.gd")
const Saves := preload("res://scripts/saves.gd")
const Music := preload("res://scripts/music.gd")
const MenuUI := preload("res://scripts/menu_ui.gd")

const AMBIENT := Color(0.50, 0.56, 0.74)
const AMBIENT_ENERGY := 2.0
## Inside (a scene.json with "rain": false) there is no moon and the sky fill is a neutral warm
## bounce, so the side of a figure away from the fire is brown or grey, not navy.
const AMBIENT_INTERIOR := Color(0.56, 0.54, 0.56)
const AMBIENT_INTERIOR_ENERGY := 2.4
const START := Vector3(-2.0, 0.0, 2.2)

var data: SceneData
var view
var world: Node3D
var cam: Camera3D
var rig
var compositor
var lights
var flipbooks
var rain
var crows
var nav
var portals
var overlay
var player: Node3D
var npcs: Array = []           # npc.gd of the people standing in this location
var npc_defs := {}             # id -> data/npcs/<id>.json, for every person in the game
var perf: CanvasLayer
var ui: CanvasLayer
var interaction
var audio
var session                    # session.gd: location, satchel, quest flags, save and load
var inventory                  # main.inventory.add(id) / has(id) / remove(id)
var quest                      # main.quest.set_flag(name) / flag(name) / get_flag(name)
var skills                     # main.skills.value("logic") / add(id, n); skills.gd
var journal                    # main.journal.update(task, text) / finish(task); journal.gd
var story                      # story.gd
var dialogue
var inventory_ui
var sheet_ui
var quest_panel
var menu                       # menu_ui.gd: title screen and pause menu
var chapter                    # chapter_ui.gd: the card and the page of choices at the end of a chapter
var pad
var clock := 0.0
var paused_clock := false


func _ready() -> void:
	Actions.install()
	Cursor.apply()
	Settings.apply()
	DisplayServer.window_set_title(MenuUI.NAME)
	var pending := Session.take_pending()
	var show_title := MenuUI.wanted(pending)
	data = SceneData.new(pending.get("location", ""))
	session = Session.new()
	session.name = "Session"
	add_child(session)
	session.setup(self, data, pending)
	inventory = session.inventory
	quest = session.quest
	skills = session.skills
	journal = session.journal
	perf = preload("res://scripts/perf.gd").new()
	add_child(perf)
	view = preload("res://scripts/view.gd").new()
	view.name = "View"
	add_child(view)
	view.setup(data)
	world = Node3D.new()
	world.name = "World3D"
	view.sv.add_child(world)
	_setup_environment()
	_setup_camera(show_title)

	compositor = _module("compositor", "Compositor")
	compositor.setup(data)
	compositor.perf = perf
	lights = _module("lights", "Lights")
	lights.setup(data, compositor)
	flipbooks = _module("flipbooks", "Flipbooks")
	flipbooks.setup(data, compositor)
	nav = _module("navigation", "Navigation")
	nav.setup(data)
	_spawn_player()
	crows = _module("crows", "Crows")
	crows.setup(data, player, data.config.get("crows", {}), data.config.get("audio", {}))
	rain = _module("rain", "Rain")
	rain.setup(rig, compositor, data.config.get("rain", {}))
	overlay = _module("debug_overlay", "Overlay")
	overlay.setup(nav, data.hotspots)
	portals = _node("portals", "Portals")
	portals.setup(nav, player)

	ui = preload("res://scripts/ui.gd").new()
	add_child(ui)
	inventory_ui = preload("res://scripts/inventory_ui.gd").new()
	add_child(inventory_ui)
	inventory_ui.setup(self, inventory, ui.font)
	sheet_ui = preload("res://scripts/sheet_ui.gd").new()
	add_child(sheet_ui)
	sheet_ui.setup(self, ui.font)
	quest_panel = preload("res://scripts/quest_panel.gd").new()
	add_child(quest_panel)
	quest_panel.setup(self)
	story = Story.new()
	story.load_file(data.config.get("story", "data/story/main.json"))
	session.attach_story(story)
	dialogue = _node("dialogue", "Dialogue")
	dialogue.setup(self, story)
	audio = _node("audio", "Audio")
	audio.setup(data, world, nav, compositor, rig)
	audio.voice_probe = dialogue.voice_active
	player.step.connect(audio.footstep)
	portals.door.connect(audio.door)
	_spawn_npcs()
	interaction = _node("interaction", "Interaction")
	interaction.setup(self)
	portals.travel.connect(func(pt): interaction.door_to({id = pt.id, pos = pt.a, label = pt.label, target = pt.to}))
	pad = _node("pad", "Pad")
	pad.setup(self)
	menu = MenuUI.new()
	menu.name = "Menu"
	add_child(menu)
	menu.setup(self)
	chapter = preload("res://scripts/chapter_ui.gd").new()
	chapter.name = "Chapter"
	add_child(chapter)
	chapter.setup(self, ui.font)
	if show_title:
		menu.open_title()
		Music.title(self)
	else:
		Music.fade_out()
	rig.settled.connect(_on_view_settled)
	if data.scene.get("rain", true) == false:
		set_rain(false)
	session.arrive()
	# debugging: --off=rain,flipbooks,crows,background hides those parts
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--off="):
			for part in arg.substr(6).split(","):
				var n = {"rain": rain, "flipbooks": flipbooks, "crows": crows, "background": compositor}.get(part)
				if n:
					n.visible = false
	if "--capture" in OS.get_cmdline_user_args():
		add_child(preload("res://scripts/capture.gd").new())
	elif Array(OS.get_cmdline_user_args()).any(func(a): return a.begins_with("--clip=")):
		add_child(preload("res://scripts/clip.gd").new())
	elif "--snap" in OS.get_cmdline_user_args():
		add_child(preload("res://scripts/snap.gd").new())
	elif Array(OS.get_cmdline_user_args()).any(func(a): return a.begins_with("--npc-check")):
		add_child(preload("res://scripts/npc_check.gd").new())
	elif "--perf-check" in OS.get_cmdline_user_args():
		add_child(preload("res://scripts/perf_check.gd").new())
	elif "--ui-check" in OS.get_cmdline_user_args():
		add_child(preload("res://scripts/ui_check.gd").new())
	elif "--menu-check" in OS.get_cmdline_user_args():
		add_child(preload("res://scripts/menu_check.gd").new())
	elif "--char-check" in OS.get_cmdline_user_args():
		add_child(preload("res://scripts/char_check.gd").new())
	elif Array(OS.get_cmdline_user_args()).any(func(a): return a.begins_with("--release-shot=")):
		add_child(preload("res://scripts/release_shot.gd").new())
	elif "--playthrough-check" in OS.get_cmdline_user_args():
		preload("res://scripts/playthrough_check.gd").start(get_tree(), "playthrough")
	elif "--release-check" in OS.get_cmdline_user_args():
		preload("res://scripts/playthrough_check.gd").start(get_tree(), "locations")
	_log_startup.call_deferred()


## Logs when loading finished and when the first frame was drawn, in ms since the engine started,
## and the video memory ten frames later.
func _log_startup() -> void:
	var loaded := Time.get_ticks_msec()
	await RenderingServer.frame_post_draw
	var first := Time.get_ticks_msec()
	for i in 10:                    # the monitor updates once per frame
		await RenderingServer.frame_post_draw
	var vram := Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0
	print("startup: loaded at %d ms, first frame at %d ms, video memory %.0f MB" % [loaded, first, vram])
	perf.startup(loaded, first, vram)


func _module(script: String, name: String) -> Node3D:
	var n := Node3D.new()
	n.set_script(load("res://scripts/%s.gd" % script))
	n.name = name
	world.add_child(n)
	return n


func _node(script: String, name: String) -> Node:
	var n := Node.new()
	n.set_script(load("res://scripts/%s.gd" % script))
	n.name = name
	add_child(n)
	return n


# ---------- camera and environment ----------

func _setup_environment() -> void:
	var env := Environment.new()
	# a blue-hour sky, never seen (the frame covers the screen) but reflected in wet feathers and
	# the figure's leather; ambient light stays the flat sky fill
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.10, 0.15, 0.30)
	sky_mat.sky_horizon_color = Color(0.25, 0.30, 0.42)
	sky_mat.sky_energy_multiplier = 3.0
	sky_mat.ground_horizon_color = Color(0.08, 0.08, 0.09)
	sky_mat.ground_bottom_color = Color(0.03, 0.03, 0.035)
	sky_mat.sun_angle_max = 0.0
	var sky := Sky.new()
	sky.sky_material = sky_mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.ambient_light_sky_contribution = 0.0
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	var interior: bool = data.scene.get("rain", true) == false
	env.ambient_light_color = AMBIENT_INTERIOR if interior else AMBIENT
	env.ambient_light_energy = AMBIENT_INTERIOR_ENERGY if interior else AMBIENT_ENERGY
	# linear, scaled down so nothing clips before the view transform (view.gd scales it back)
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.tonemap_exposure = 1.0 / view.PRESCALE
	var we := WorldEnvironment.new()
	we.environment = env
	world.add_child(we)
	var amb: Dictionary = data.scene.ambient
	var moon := DirectionalLight3D.new()
	var m: Dictionary = amb.moon
	moon.light_color = Color(m.color[0], m.color[1], m.color[2])
	moon.light_energy = 0.0 if interior else 0.12
	var d := SceneData.v3(amb.moon_direction)
	world.add_child(moon)
	moon.look_at_from_position(Vector3.ZERO, d, Vector3.UP if absf(d.y) < 0.99 else Vector3.FORWARD)


func _setup_camera(show_title: bool) -> void:
	var c: Dictionary = data.scene.camera
	cam = Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.keep_aspect = Camera3D.KEEP_WIDTH
	cam.size = c.ortho_width_m
	cam.near = c.near
	cam.far = c.far
	var b := Basis(SceneData.v3(c.basis_x), SceneData.v3(c.basis_y), SceneData.v3(c.basis_z))
	cam.transform = Transform3D(b, SceneData.v3(c.origin))
	world.add_child(cam)
	cam.current = true
	rig = preload("res://scripts/camera_rig.gd").new()
	rig.name = "CameraRig"
	add_child(rig)
	var cfg: Dictionary = data.config.get("camera", {})
	if show_title:
		cfg = cfg.merged({intro = true}, true)
		data.config.camera = cfg
	elif "--no-intro" in OS.get_cmdline_user_args() or session.skip_intro:
		cfg = cfg.merged({intro = false}, true)
		data.config.camera = cfg
	rig.setup(data, cam, cfg)
	if show_title:
		rig.hold_intro()


## New game: the build chosen on the title screen goes into the skills and the held intro plays.
func begin_game(archetype: String, build: Dictionary) -> void:
	skills.apply_build(archetype, build)
	Music.fade_out()
	rig.begin_intro()


func _on_view_settled() -> void:
	# the wide view is only seen in the intro
	if not rig.in_intro() and rig.zoom >= 0.999 and not compositor.wide.is_empty():
		compositor.drop_wide()
		rain.drop_wide()


# ---------- screen pixels <-> world ----------

## The world point the screen shows at a screen (canvas) pixel.
func world_at(px: Vector2) -> Vector3:
	var vp: Vector2 = view.frame_to_view(px)
	var o := cam.project_ray_origin(vp)
	var dir := cam.project_ray_normal(vp)
	var depth: float = compositor.depth_at(rig.screen_to_frame(px))
	var t: float = depth - (o - rig.origin).dot(rig.fwd)
	return o + dir * t / dir.dot(rig.fwd)


## Screen (canvas) pixel of a world point.
func screen_of(p: Vector3) -> Vector2:
	return view.view_to_frame(cam.unproject_position(p))


# ---------- people ----------

## Every data/npcs/<id>.json is known; the ones standing in this location get a figure. A person
## whose own location has no export stands at their `fallback` place instead (see npc.gd).
func _spawn_npcs() -> void:
	var dir := "data/npcs"
	for f in DirAccess.get_files_at(SceneData.res(dir)):
		if f.ends_with(".json"):
			var def = JSON.parse_string(FileAccess.get_file_as_string("%s/%s" % [SceneData.res(dir), f]))
			npc_defs[def.id] = def
	for id in npc_defs:
		var def := _placed(npc_defs[id])
		if not def.is_empty():
			var n = preload("res://scripts/npc.gd").new()
			world.add_child(n)
			n.setup(self, def)
			npcs.append(n)
	if not npcs.is_empty():
		print("people: %s" % ", ".join(npcs.map(func(n): return n.display_name())))


func _placed(def: Dictionary) -> Dictionary:
	var home: String = def.get("location", Locations.start(data.config))
	if home == data.location:
		return def
	var fb: Dictionary = def.get("fallback", {})
	if fb.get("location", "") == data.location and not Locations.exists(data.config, home):
		return def.merged(fb, true)
	return {}


func npc_by_id(id: String):
	for n in npcs:
		if n.def.id == id:
			return n
	return null


## The name shown above a person's lines, also for one who is not standing here.
func npc_name(id: String) -> String:
	return npc_defs.get(id, {}).get("name", id.capitalize())


# ---------- player ----------

func _spawn_player() -> void:
	player = preload("res://scripts/player.gd").new()
	player.name = "Player"
	player.nav = nav
	world.add_child(player)
	player.global_position = START


# ---------- per frame ----------

func _process(delta: float) -> void:
	if not paused_clock:
		clock += delta
	var t := clock
	rig.update(delta)
	var vr: Rect2 = rig.view_rect()
	compositor.set_view(vr, Vector2(view.sv.size), rig.zoom)
	compositor.update(t)
	flipbooks.set_view(vr, rig.frame, compositor.tile.get("rect", Rect2()), compositor.tile_mix)
	lights.update(t)
	flipbooks.update(t)
	rain.update(t, compositor)
	crows.update(t, delta)
	portals.update()
	interaction.update()
	audio.update(player.global_position, cam.global_basis)


# ---------- input ----------

func _unhandled_input(event: InputEvent) -> void:
	if menu.is_open():
		return
	if event.is_action("highlight_all") and not (event is InputEventKey and event.echo):
		interaction.set_tab(event.is_pressed())
		return
	if ui.busy or session.traveling:
		return
	if event.is_action_pressed("back"):
		if sheet_ui.is_open():
			sheet_ui.close()
		elif inventory_ui.is_open():
			inventory_ui.close()
		elif ui.is_open():
			ui.close()
		else:
			interaction.set_selected(null)
		return
	if event.is_action_pressed("inventory"):
		sheet_ui.close()
		inventory_ui.toggle()
		return
	if event.is_action_pressed("sheet"):
		sheet_ui.toggle("sheet")
		return
	if event.is_action_pressed("journal"):
		sheet_ui.toggle("journal")
		return
	if event.is_action_pressed("quick_save"):
		inventory_ui.toast("Not in the middle of a conversation" if ui.is_open() else "Saved" if session.save(Saves.QUICK) else "Could not save")
		return
	if event.is_action_pressed("quick_load"):
		if not session.load_save(Saves.QUICK):
			inventory_ui.toast("Nothing to load")
		return
	if inventory_ui.is_open() or sheet_ui.is_open():
		return
	if event is InputEventMouseMotion:
		interaction.update_hover(event.position)
	elif event is InputEventMouseButton and event.pressed and event.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT]:
		interaction.click(event.position, event.shift_pressed or event.button_index == MOUSE_BUTTON_RIGHT)
	elif event is InputEventKey and event.pressed:
		match event.keycode:
			KEY_F1:
				overlay.visible = not overlay.visible
				quest_panel.visible = overlay.visible
			KEY_F2:
				set_rain(not rain.visible)
			KEY_SHIFT:
				interaction.update_hover(get_viewport().get_mouse_position())


func set_rain(on: bool) -> void:
	rain.visible = on
	compositor.set_rain(on)


# capture.gd calls these
func update_hover(px: Vector2) -> void:
	interaction.update_hover(px)


func click(px: Vector2, force := false) -> void:
	interaction.click(px, force)
