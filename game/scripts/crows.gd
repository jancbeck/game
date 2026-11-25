## The crows: live birds from crow.glb on the perches of scene.json. They take off when the
## figure comes within flee_radius_m, with any neighbour close by following a moment later, fly to
## a free perch away from the figure, and call as they go. Now and then one flies off on its own.
##
## scene.json -> crows {model, perches [{id, pos, yaw (deg)}], start [perch ids]}.
## config.json -> crows {flee_radius_m, solo_flight_s [min, max], wing_spread_deg}.
extends Node3D

const SceneData := preload("res://scripts/scene_data.gd")
const Curves := preload("res://scripts/curves.gd")
const CrowScript := preload("res://scripts/crow.gd")

var perches: Array = []        # [{id, pos, yaw}]
var crows: Array = []
var taken := {}                # perch id -> crow
var player: Node3D
var flee_radius := 3.0
var solo_range := Vector2(18, 40)
var next_solo := 20.0
var calls: Array = []          # AudioStream
var rng := RandomNumberGenerator.new()
var clock := 0.0


func setup(data: SceneData, figure: Node3D, cfg: Dictionary, audio_cfg: Dictionary) -> void:
	player = figure
	rng.seed = 7
	flee_radius = float(cfg.get("flee_radius_m", 3.0))
	var sr: Array = cfg.get("solo_flight_s", [18, 40])
	solo_range = Vector2(sr[0], sr[1])
	next_solo = rng.randf_range(solo_range.x * 0.5, solo_range.y * 0.5)
	var c: Dictionary = data.scene.get("crows", {})
	if c.is_empty():
		return
	for p in c.get("perches", []):
		perches.append({id = p.id, pos = SceneData.v3(p.pos), yaw = deg_to_rad(float(p.get("yaw", 0.0)))})
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	if doc.append_from_file(SceneData.abs_path(c.model), state) != OK:
		push_error("cannot load crow model " + c.model)
		return
	var proto := doc.generate_scene(state)
	for path in audio_cfg.get("crows", []):
		if FileAccess.file_exists(SceneData.res(path)):
			calls.append(AudioStreamWAV.load_from_file(SceneData.abs_path(path)))
	var spread := deg_to_rad(float(cfg.get("wing_spread_deg", 80.0)))
	for id in c.get("start", []):
		var p = _perch(id)
		if p == null:
			continue
		var crow := Node3D.new()
		crow.set_script(CrowScript)
		crow.name = "crow_" + String(id)
		add_child(crow)
		crow.spread = spread
		crow.setup(proto.duplicate(), Curves.seed_of(String(id)), p.merged({home_yaw = p.yaw}))
		crow.took_off.connect(_on_took_off)
		taken[p.id] = crow
		crows.append(crow)
	proto.free()
	print("crows: %d on %d perches" % [crows.size(), perches.size()])


func _perch(id):
	for p in perches:
		if p.id == id:
			return p
	return null


func _free_perches(from: Vector3, away_from: Vector3, min_away: float) -> Array:
	var out := []
	for p in perches:
		if taken.has(p.id):
			continue
		var crowded := false
		for other in taken:
			var q = _perch(other)
			if q and q.pos.distance_to(p.pos) < 1.0:
				crowded = true
				break
		if crowded:
			continue
		if p.pos.distance_to(away_from) < min_away:
			continue
		var d: float = p.pos.distance_to(from)
		if d < 3.0 or d > 24.0:
			continue
		out.append(p)
	return out


## Sends a crow to a free perch; prefers high perches and ones 6-16 m away. False if none is free.
func send(crow, t: float, away_from: Vector3, min_away := 4.0) -> bool:
	var options := _free_perches(crow.perch.pos, away_from, min_away)
	if options.is_empty():
		return false
	var best = null
	var best_score := -INF
	for p in options:
		var d: float = p.pos.distance_to(crow.perch.pos)
		var score: float = -absf(d - 10.0) * 0.3 + p.pos.y * 0.25 + rng.randf() * 2.0
		if score > best_score:
			best = p
			best_score = score
	taken.erase(crow.perch.id)
	taken[best.id] = crow
	crow.fly_to(best.merged({home_yaw = best.yaw}), t)
	return true


func update(t: float, dt: float) -> void:
	clock = t
	var feet := player.global_position
	for crow in crows:
		if not crow.flying and crow.global_position.distance_to(feet + Vector3(0, 0.9, 0)) < flee_radius + 0.9:
			if send(crow, t, feet, flee_radius + 3.0):
				# neighbours on the same roof go up a moment later
				for other in crows:
					if other != crow and not other.flying and other.perch.pos.distance_to(crow.global_position) < 2.5:
						get_tree().create_timer(rng.randf_range(0.15, 0.6)).timeout.connect(_follow.bind(other, feet))
	if t >= next_solo:
		next_solo = t + rng.randf_range(solo_range.x, solo_range.y)
		var idle := crows.filter(func(c): return not c.flying and c.global_position.distance_to(feet) > flee_radius * 2.0)
		if not idle.is_empty():
			send(idle[rng.randi_range(0, idle.size() - 1)], t, feet, flee_radius)
	for crow in crows:
		crow.update(t)


func _follow(crow, away_from: Vector3) -> void:
	if not crow.flying:
		send(crow, clock, away_from, flee_radius + 3.0)


func _on_took_off(crow) -> void:
	if calls.is_empty() or rng.randf() < 0.25:
		return
	var p := AudioStreamPlayer3D.new()
	p.bus = "Sfx"
	p.stream = calls[rng.randi_range(0, calls.size() - 1)]
	p.unit_size = 6.0
	p.volume_db = -4.0
	p.max_db = 0.0
	crow.add_child(p)
	var length: float = p.stream.get_length()
	p.play(rng.randf_range(0.0, maxf(0.0, length - 2.0)))
	# a tween on the player stops with it, when a location change frees the crow first
	var tw := p.create_tween()
	tw.tween_interval(rng.randf_range(1.0, 1.8))
	tw.tween_property(p, "volume_db", -40.0, 0.3)
	tw.tween_callback(p.queue_free)


## Next solo flight now (capture runs).
func solo_now() -> void:
	next_solo = clock
