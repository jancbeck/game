## Doors the figure goes through (scene.json -> walk.portals [{id, a, b, label, seconds, sound}]).
##
## Walking into either end opens the door, the figure goes inside and the door closes behind it;
## after `seconds` the door at the other end opens, the figure steps out a little way and that
## door closes. route() finds a way through a portal when a clicked point is on another part of
## the walk mesh (the courtyard, the stair, the wall-walks are separate islands).
extends Node

signal door(sound: String, action: String, pos: Vector3)
signal transit_started(portal)
signal transit_finished(portal)
signal travel(portal)          # the figure walked into a door out to another location (portal.to)

const ENTER_M := 0.55          # how close to an end the figure must come
const REARM_M := 1.2           # after stepping out, the end is quiet until the figure is this far

var nav
var player
var busy := false
var _quiet = null              # [portal, end Vector3] the figure just came out of
var _then := Vector3.INF       # where to walk after the transit (a routed click)


func setup(navigation, figure) -> void:
	nav = navigation
	player = figure
	print("portals: %s" % ", ".join(nav.portals.map(func(p): return "%s (%.1f s)" % [p.id, p.seconds])))


## The ends of a portal the figure can walk into: both, or only `a` for a door out to another location.
func door_ends(pt: Dictionary) -> Array:
	return [pt.a] if pt.to != "" else [pt.a, pt.b]


## The portal end a world point lies near (for hover and clicks): [portal, end] or null.
func near(p: Vector3, reach := 1.3):
	for pt in nav.portals:
		for e in door_ends(pt):
			var d: Vector3 = p - e
			if Vector2(d.x, d.z).length() < reach and d.y > -0.6 and d.y < 3.0:
				return [pt, e]
	return null


## A walk to `goal` through a portal when no direct path reaches it: walks to the near end and
## remembers the goal. Returns false when no portal connects the two.
func route(goal: Vector3) -> bool:
	var from: Vector3 = player.global_position
	for pt in nav.portals:
		if pt.to != "":
			continue
		for ends in [[pt.a, pt.b], [pt.b, pt.a]]:
			var a: Vector3 = nav.nav_point(ends[0])
			var b: Vector3 = nav.nav_point(ends[1])
			if nav.reachable(from, a) and nav.reachable(b, goal):
				_then = goal
				_quiet = null
				return player.walk_to(a)
	return false


func clear_route() -> void:
	_then = Vector3.INF


func update() -> void:
	if busy:
		return
	var p: Vector3 = player.global_position
	if _quiet != null:
		var dq: Vector3 = p - _quiet[1]
		if Vector2(dq.x, dq.z).length() > REARM_M or absf(dq.y) > 1.5:
			_quiet = null
		return
	for pt in nav.portals:
		for ends in [[pt.a, pt.b], [pt.b, pt.a]]:
			if pt.to != "" and ends[0] != pt.a:
				continue
			var d: Vector3 = p - ends[0]
			if Vector2(d.x, d.z).length() < ENTER_M and absf(d.y) < 1.0:
				if pt.to != "":
					_quiet = [pt, ends[0]]
					travel.emit(pt)
				else:
					_transit(pt, ends[0], ends[1])
				return


func _transit(pt: Dictionary, from: Vector3, to: Vector3) -> void:
	busy = true
	transit_started.emit(pt)
	player.stop()
	player.face(from + (from - player.global_position) * 2.0)
	door.emit(pt.sound, "open", from)
	var tree := get_tree()
	await tree.create_timer(0.45).timeout
	player.visible = false
	await tree.create_timer(0.55).timeout
	door.emit(pt.sound, "close", from)
	await tree.create_timer(maxf(0.2, pt.seconds - 1.0)).timeout
	var out: Vector3 = nav.nav_point(to)
	player.global_position = out
	door.emit(pt.sound, "open", to)
	await tree.create_timer(0.35).timeout
	player.visible = true
	_quiet = [pt, to]
	busy = false
	var goal := _then
	_then = Vector3.INF
	if goal != Vector3.INF:
		player.walk_to(goal)
	else:
		# step out of the doorway onto the walk
		var step := step_out(out)
		if step.distance_to(out) > 0.3:
			player.walk_to(step)
	await tree.create_timer(0.8).timeout
	door.emit(pt.sound, "close", to)
	transit_finished.emit(pt)


## A walkable point about a metre from a door: of eight directions, the one with the most
## walkable ground around it.
func step_out(at: Vector3) -> Vector3:
	var best := at
	var best_score := -1.0
	for k in 8:
		var dir := Vector3(cos(k * PI / 4.0), 0.0, sin(k * PI / 4.0))
		var q: Vector3 = nav.nav_point(at + dir * 1.1)
		var score := 0.0
		for r in [0.6, 1.1, 1.6]:
			var s: Vector3 = nav.nav_point(at + dir * r)
			if s.distance_to(at + dir * r) < 0.15:
				score += 1.0
		if score > best_score:
			best_score = score
			best = q
	return best
