## Sound: the rain bed and the fire basket's loop, footsteps by surface, click sounds, each
## hotspot's own sound when the figure interacts with it, and doors at portals.
##
## An interior (its scene.json says "rain": false) has no rain bed: it gets the fire loop at the
## room's own hearth and a quiet, low room tone, no reverb. The room tone is config.json -> audio ->
## room (a loop under game/); while that file is missing a steady low rumble is made in code.
##
## Data: the sounds.json named in config.json -> sounds (contract: game/data/sounds.json) with
## footsteps {surface: [wav]}, click {walk, interact}, hotspots {id: [wav]},
## portals {sound: {open, close}}, levels_db {rain_bed, fire, footsteps, click, hotspots, doors}.
## config.json -> audio {rain, fire, fire_group, room, crows} keeps the loops; fire_group is the id of
## a light group, or a list of ids of which the location's first one anchors the fire loop.
##
## Three buses under Master: "Ambience" (rain bed, fire loop), "Voice" (people and the skills'
## clips) and "Sfx" (everything else); settings.gd sets the volumes the player chose. The ambience
## ducks a few dB while a voice plays (`voice_probe`), and its bus volume is the zoom's, the duck
## and the player's setting added up. The zoom moves the
## ear: the rain and ambience are distant in the wide view (quieter, darker) and close at zoom 2
## (louder, brighter); positional sounds are heard from a point that backs away from the figure as
## the view widens. No reverb: the courtyard is open to the sky, the recordings carry their own
## outdoor space, and Godot's reverb makes it sound like a barrel.
extends Node

const SceneData := preload("res://scripts/scene_data.gd")
const Settings := preload("res://scripts/settings.gd")

const DUCK_DB := -8.0           # the ambience under a voice
const DUCK_ATTACK_S := 0.15     # time to reach the full duck
const DUCK_RELEASE_S := 0.7     # time to come back

var sounds := {}
var levels := {}
var ear: AudioListener3D
var world: Node3D
var nav
var compositor
var rig
var _streams := {}              # path -> AudioStreamWAV
var _pool: Array[AudioStreamPlayer3D] = []
var _pool_i := 0
var _ui: AudioStreamPlayer
var _last := {}                 # key -> last variant index
var rng := RandomNumberGenerator.new()
var _amb_bus := -1
var _lp: AudioEffectLowPassFilter
var bed: AudioStreamPlayer
var interior := false
var room: AudioStreamPlayer       # the room tone of an interior
var fire_player: AudioStreamPlayer3D
var last_step := ""             # surface of the last footstep (for checks)
var voice_probe := Callable()   # () -> bool: a voice is playing (main.gd sets it to the dialogue's)
var duck_db := 0.0              # how far the ambience is pulled down now (0 to DUCK_DB)
var _zoom_db := 0.0             # the ambience bus level the zoom asks for


func setup(data: SceneData, world3d: Node3D, navigation, comp, camera_rig) -> void:
	world = world3d
	nav = navigation
	compositor = comp
	rig = camera_rig
	rng.seed = 11
	var path: String = data.config.get("sounds", "data/sounds.json")
	if FileAccess.file_exists(SceneData.res(path)):
		sounds = SceneData._json(path)
		print("sounds: %s%s" % [path, " (STAND-IN)" if path.begins_with("assets_stub") else ""])
	else:
		push_warning("no %s: footsteps, clicks, hotspot and door sounds are silent" % path)
	levels = sounds.get("levels_db", {})
	_setup_buses()
	var a: Dictionary = data.config.get("audio", {})
	interior = data.scene.get("rain", true) == false
	if interior:
		var tone := _wav(a.get("room", ""), true)
		room = AudioStreamPlayer.new()
		room.stream = tone if tone else _room_tone()
		room.volume_db = float(levels.get("room", -26.0))
		room.bus = "Ambience"
		add_child(room)
		room.play()
	else:
		var rain_loop := _wav(a.get("rain", ""), true)
		if rain_loop:
			bed = AudioStreamPlayer.new()
			bed.stream = rain_loop
			bed.volume_db = float(levels.get("rain_bed", -20.0))
			bed.bus = "Ambience"
			add_child(bed)
			bed.play()
	var fire := _wav(a.get("fire", ""), true)
	var fire_groups: Array = a.get("fire_group") if a.get("fire_group") is Array else [a.get("fire_group", "")]
	var g = null
	for cand in compositor.groups:
		if cand.id in fire_groups:
			g = cand
	if fire and g:
		fire_player = AudioStreamPlayer3D.new()
		fire_player.stream = fire
		fire_player.position = g.anchor
		fire_player.unit_size = 2.0
		fire_player.volume_db = float(levels.get("fire", -6.0))
		fire_player.bus = "Ambience"
		world.add_child(fire_player)
		fire_player.play()
	for i in 10:
		var p := AudioStreamPlayer3D.new()
		p.bus = "Sfx"
		p.unit_size = 4.0
		p.max_polyphony = 1
		world.add_child(p)
		_pool.append(p)
	_ui = AudioStreamPlayer.new()
	_ui.bus = "Sfx"
	add_child(_ui)
	# heard from the figure (or behind it in wider views), oriented like the camera
	ear = AudioListener3D.new()
	world.add_child(ear)
	ear.make_current()


## A steady low rumble for a room without a recording: brown noise under 200 Hz, 12 s, the end
## faded into the start so it loops without a seam.
func _room_tone() -> AudioStreamWAV:
	const RATE := 8000
	const LENGTH := RATE * 12
	const FADE := RATE
	var r := RandomNumberGenerator.new()
	r.seed = 5
	var x := PackedFloat32Array()
	x.resize(LENGTH + FADE)
	var brown := 0.0
	var low := 0.0
	var k := 1.0 - exp(-TAU * 200.0 / RATE)
	var peak := 0.0001
	for i in x.size():
		brown = brown * 0.998 + r.randf_range(-1.0, 1.0) * 0.05
		low += (brown - low) * k
		x[i] = low
		peak = maxf(peak, absf(low))
	var bytes := PackedByteArray()
	bytes.resize(LENGTH * 2)
	for i in LENGTH:
		var v := x[i] if i >= FADE else lerpf(x[LENGTH + i], x[i], float(i) / FADE)
		bytes.encode_s16(i * 2, int(clampf(v / peak * 0.8, -1.0, 1.0) * 32767.0))
	var s := AudioStreamWAV.new()
	s.format = AudioStreamWAV.FORMAT_16_BITS
	s.mix_rate = RATE
	s.data = bytes
	s.loop_mode = AudioStreamWAV.LOOP_FORWARD
	s.loop_begin = 0
	s.loop_end = LENGTH
	return s


func _setup_buses() -> void:
	for name in ["Ambience", "Voice", "Sfx"]:
		if AudioServer.get_bus_index(name) == -1:
			AudioServer.add_bus()
			AudioServer.set_bus_name(AudioServer.bus_count - 1, name)
			AudioServer.set_bus_send(AudioServer.bus_count - 1, "Master")
	_amb_bus = AudioServer.get_bus_index("Ambience")
	# a location change builds this node again on the same buses: start from no effects
	for i in range(AudioServer.get_bus_effect_count(_amb_bus) - 1, -1, -1):
		AudioServer.remove_bus_effect(_amb_bus, i)
	_lp = AudioEffectLowPassFilter.new()
	_lp.cutoff_hz = 12000.0
	AudioServer.add_bus_effect(_amb_bus, _lp)
	Settings.apply()


func _wav(path: String, loop := false) -> AudioStreamWAV:
	if path == "" or not FileAccess.file_exists(SceneData.res(path)):
		return null
	if _streams.has(path) and not loop:
		return _streams[path]
	var s := AudioStreamWAV.load_from_file(SceneData.abs_path(path))
	if s and loop:
		s.loop_mode = AudioStreamWAV.LOOP_FORWARD
		s.loop_begin = 0
		s.loop_end = int(s.get_length() * s.mix_rate)
	elif s:
		_streams[path] = s
	return s


## A random variant of a list, never the same twice in a row.
func _pick(key: String, list: Array) -> String:
	if list.is_empty():
		return ""
	var i := rng.randi_range(0, list.size() - 1)
	if list.size() > 1 and i == _last.get(key, -1):
		i = (i + 1) % list.size()
	_last[key] = i
	return list[i]


func _play_at(path: String, pos: Vector3, db: float, pitch := 1.0) -> void:
	var s := _wav(path)
	if s == null:
		return
	var p := _pool[_pool_i]
	_pool_i = (_pool_i + 1) % _pool.size()
	p.stream = s
	p.global_position = pos
	p.volume_db = db
	p.pitch_scale = pitch
	p.play()


# ---------- events ----------

func footstep(foot: Vector3) -> void:
	var steps: Dictionary = sounds.get("footsteps", {})
	if steps.is_empty():
		return
	var surf: String = nav.surface_at(foot)
	if surf == "":
		surf = "cobble"
	if surf in ["cobble", "mud", "straw"] and steps.has("puddle"):
		if compositor.mask_at("puddle", rig.frame_px_of(foot)) > 0.45:
			surf = "puddle"
	if not steps.has(surf):
		surf = "cobble" if steps.has("cobble") else steps.keys()[0]
	last_step = surf
	_play_at(_pick("step_" + surf, steps[surf]), foot, float(levels.get("footsteps", -8.0)) + rng.randf_range(-1.5, 1.5),
		rng.randf_range(0.95, 1.05))


func click(kind: String) -> void:
	var c: Dictionary = sounds.get("click", {})
	var s := _wav(c.get(kind, ""))
	if s:
		_ui.stream = s
		_ui.volume_db = float(levels.get("click", -10.0))
		_ui.play()


func hotspot(id: String, pos: Vector3) -> void:
	var list: Array = sounds.get("hotspots", {}).get(id, [])
	_play_at(_pick("hs_" + id, list), pos, float(levels.get("hotspots", -8.0)))


func door(sound: String, action: String, pos: Vector3) -> void:
	var d: Dictionary = sounds.get("portals", {}).get(sound, {})
	_play_at(d.get(action, ""), pos + Vector3(0, 1.0, 0), float(levels.get("doors", -6.0)), rng.randf_range(0.97, 1.03))


# ---------- per frame ----------

## The ambience bus: the zoom's level, the duck under a voice and the player's volume.
func refresh() -> void:
	AudioServer.set_bus_volume_db(_amb_bus, _zoom_db + duck_db + Settings.db("ambience"))


func update(player_pos: Vector3, cam_basis: Basis) -> void:
	var z: float = rig.zoom
	# 0 at zoom 0.5, 0.5 at zoom 1, 1 at zoom 2 (log scale)
	var u := clampf((log(z) / log(2.0) + 1.0) * 0.5, 0.0, 1.0)
	var near := u * 2.0 - 1.0          # -1 wide, 0 main, +1 close
	_zoom_db = 6.0 * near if near < 0.0 else 2.5 * near
	var speaking: bool = voice_probe.is_valid() and voice_probe.call()
	var target := DUCK_DB if speaking else 0.0
	var seconds := DUCK_ATTACK_S if target < duck_db else DUCK_RELEASE_S
	duck_db = move_toward(duck_db, target, absf(DUCK_DB) / seconds * get_process_delta_time())
	refresh()
	_lp.cutoff_hz = exp(lerpf(log(2600.0), log(12000.0), clampf(near + 1.0, 0.0, 1.0))) if near < 0.0 else lerpf(12000.0, 20000.0, near)
	# the ear backs away from the figure along the camera axis as the view widens
	var back := lerpf(16.0, 5.0, clampf(near + 1.0, 0.0, 1.0)) if near < 0.0 else lerpf(5.0, 0.5, near)
	ear.global_transform = Transform3D(cam_basis, player_pos + Vector3(0, 1.6, 0) - rig.fwd * back)
