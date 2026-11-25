## What the pointer means: hover, clicks, the outline, interactions and exits.
##
## Click rule: a click on a walkable surface walks there, even on a hotspot's own boards (the
## gallows deck, the well's step); a click on the object itself, where nothing is walkable within
## WALK_TOLERANCE_M, interacts. Shift-click or a right click interacts with whatever hotspot is
## under the pointer. Doorways (exits and portal ends) answer to clicks near them.
##
## Which hotspot is under the pointer comes from the ids masks (compositor.id_at), or from the
## hotspots' click boxes when the data has no ids. People (npc.gd) are live figures, tested first
## by their screen box; a click on one walks to its stand point and starts the conversation.
##
## Highlight in the manner of Disco Elysium: the hotspot the click would interact with glows
## (outline from the ids mask, background.gdshader); over its walkable part it glows faintly.
## Holding Tab (or LB, X on the pad) outlines every hotspot and shows their names.
##
## With a pad there is no pointer: pad.gd picks a target (`selected`) among candidates() and the
## hover highlight and label follow it; confirm acts on it like a click would (act()).
extends Node

const SceneData := preload("res://scripts/scene_data.gd")
const WALK_TOLERANCE_M := 0.4
const FOCUS_ZOOM := 2.0

var main
var hovered = null            # what a click would do: {kind, hotspot?, exit?, portal?, point}
var pending = null            # hotspot or exit the figure is walking to
var talking = null            # hotspot whose dialogue is open
var talking_npc = null        # npc.gd whose conversation is open
var selected = null           # the target a pad picked, same shape as `hovered`
var pad_mode := false         # a pad is in use: the pointer's hover is ignored
var tab_held := false
var _exit_cooldown = null
var _hover_px := Vector2(-1, -1)


func setup(m) -> void:
	main = m
	main.ui.closed.connect(_on_dialogue_closed)
	main.player.arrived.connect(_on_arrived)


# ---------- what is under the pointer ----------

func hotspot_index(h: Dictionary) -> int:
	return main.data.hotspots.find(h) + 1


func hotspot_at(px: Vector2):
	var fpx: Vector2 = main.rig.screen_to_frame(px)
	var k: int = main.compositor.id_at(fpx)
	if k > 0 and k <= main.data.hotspots.size():
		return main.data.hotspots[k - 1]
	if k == 0:
		return null
	return _hotspot_by_volume(main.world_at(px))


func _hotspot_by_volume(p: Vector3):
	# the courtyard floor around and under a prop is not the prop
	if p.y < 0.06:
		return null
	var best = null
	var best_vol := INF
	for h in main.data.hotspots:
		var v: Dictionary = h.volume
		var local := Basis(Vector3.UP, -float(v.yaw_rad)) * (p - SceneData.v3(v.center))
		var half := SceneData.v3(v.size) * 0.5 + Vector3.ONE * 0.1
		if absf(local.x) <= half.x and absf(local.y) <= half.y and absf(local.z) <= half.z:
			var vol: float = v.size[0] * v.size[1] * v.size[2]
			if vol < best_vol:
				best = h
				best_vol = vol
	return best


## What a click at screen px does; force = Shift or right button.
func target_at(px: Vector2, force := false) -> Dictionary:
	var p: Vector3 = main.world_at(px)
	for n in main.npcs:
		if n.hit(px):
			return {kind = "npc", npc = n, point = p}
	var h = hotspot_at(px)
	var q: Vector3 = main.nav.nav_point(p)
	var walkable: bool = q.distance_to(p) < WALK_TOLERANCE_M
	if h and (force or not walkable):
		return {kind = "hotspot", hotspot = h, point = p, walkable = walkable}
	var pt = main.portals.near(p)
	if pt:
		return {kind = "portal", portal = pt[0], end = pt[1], point = p}
	var e = main.nav.exit_near(p)
	if e:
		return {kind = "exit", exit = e, point = p}
	return {kind = "walk", point = q, walkable = walkable, hotspot = h}


func update_hover(px: Vector2) -> void:
	_hover_px = px
	if not main.nav.ready_map():
		return
	if main.ui.busy or main.ui.is_open():
		hovered = null
		main.ui.show_hover("", px)
		_apply_highlight()
		return
	if selected != null:
		hovered = selected
		main.ui.show_hover(label_of(selected), main.screen_of(anchor_of(selected)))
	elif pad_mode:
		hovered = null
		main.ui.show_hover("", px)
	else:
		hovered = target_at(px, Input.is_key_pressed(KEY_SHIFT))
		var label := label_of(hovered)
		Input.set_default_cursor_shape(Input.CURSOR_POINTING_HAND if label != "" else Input.CURSOR_ARROW)
		main.ui.show_hover(label, px)
	_apply_highlight()


## The name shown for a target ("" when it has none).
func label_of(t: Dictionary) -> String:
	match t.kind:
		"hotspot":
			return t.hotspot.name
		"npc":
			return t.npc.display_name()
		"exit":
			return t.exit.label
		"portal":
			var pt: Dictionary = t.portal
			return pt.get("label_b", pt.label) if t.end == pt.b else pt.label
	return ""


## The world point a target's name hangs at.
func anchor_of(t: Dictionary) -> Vector3:
	match t.kind:
		"hotspot":
			return SceneData.v3(t.hotspot.position) + Vector3(0, 0.3, 0)
		"npc":
			return t.npc.figure.global_position + Vector3(0, 1.9, 0)
		"exit":
			return t.exit.pos + Vector3(0, 1.2, 0)
		"portal":
			return t.end + Vector3(0, 1.2, 0)
	return t.point


## What a pad can pick near the figure, nearest first: [{target, pos (world), dist}]. Only things
## on the figure's own level count (the wall-walk does not offer the yard's well).
func candidates(reach_m: float) -> Array:
	var me: Vector3 = main.player.global_position
	var list := []
	for h in main.data.hotspots:
		var at := SceneData.v3(h.stand) if h.has("stand") else SceneData.v3(h.position)
		list.append([{kind = "hotspot", hotspot = h, point = SceneData.v3(h.position), walkable = false}, SceneData.v3(h.position), at])
	for n in main.npcs:
		list.append([{kind = "npc", npc = n, point = n.figure.global_position}, n.figure.global_position, n.stand_point()])
	for e in main.nav.exits:
		list.append([{kind = "exit", exit = e, point = e.pos}, e.pos, e.pos])
	for pt in main.nav.portals:
		for end in main.portals.door_ends(pt):
			list.append([{kind = "portal", portal = pt, end = end, point = end}, end, end])
	var out := []
	for c in list:
		var at: Vector3 = c[2]
		var d := Vector2(at.x - me.x, at.z - me.z).length()
		if d <= reach_m and absf(at.y - me.y) < 3.0:
			out.append({target = c[0], pos = c[1], dist = d})
	out.sort_custom(func(a, b): return a.dist < b.dist)
	return out


func set_selected(t) -> void:
	selected = t
	update_hover(_hover_px)


func set_pad_mode(on: bool) -> void:
	pad_mode = on
	main.ui.pad_mode = on
	if not on:
		selected = null
	if on or _hover_px.x >= 0.0:
		update_hover(_hover_px)


func _apply_highlight() -> void:
	var s := {}
	if tab_held and not main.ui.is_open():
		for i in main.data.hotspots.size():
			s[i + 1] = 0.6
	if hovered:
		if hovered.kind == "hotspot":
			s[hotspot_index(hovered.hotspot)] = 1.0
		elif hovered.kind == "walk" and hovered.get("hotspot"):
			var k := hotspot_index(hovered.hotspot)
			s[k] = maxf(s.get(k, 0.0), 0.3)
	if talking:
		s = {hotspot_index(talking): 0.5}
	main.compositor.set_highlight(s)
	if tab_held and not main.ui.is_open():
		var tags := []
		for h in main.data.hotspots:
			if hovered and hovered.kind == "hotspot" and hovered.hotspot == h:
				continue   # the hover label names it already
			tags.append([h.name, main.screen_of(SceneData.v3(h.position) + Vector3(0, 0.3, 0))])
		main.ui.show_tags(tags)
	else:
		main.ui.show_tags([])


func set_tab(on: bool) -> void:
	tab_held = on
	_apply_highlight()


## Per frame: the view moves under a still pointer, so hover follows it.
func update() -> void:
	if (_hover_px.x >= 0.0 or selected != null) and (main.rig.zoom != 1.0 or tab_held or selected != null):
		update_hover(_hover_px)
	_check_exits()


# ---------- clicks ----------

func click(px: Vector2, force := false) -> void:
	if main.portals.busy:
		return
	act(target_at(px, force))


## Does what a click on target `t` does: walks there and interacts, takes the door, or just walks.
func act(t: Dictionary) -> void:
	if main.portals.busy:
		return
	main.ui.close()
	main.portals.clear_route()
	match t.kind:
		"hotspot":
			var h: Dictionary = t.hotspot
			main.audio.click("interact")
			main.compositor.request_tile(h.id)
			pending = h
			var goal: Vector3 = main.nav.nav_point(SceneData.v3(h.stand) if h.has("stand") else SceneData.v3(h.position))
			if goal.distance_to(main.player.global_position) < 0.15:
				_on_arrived()
			elif not _walk(goal):
				pending = null
		"npc":
			main.audio.click("interact")
			pending = {npc = t.npc}
			if not _walk(main.nav.nav_point(t.npc.stand_point())):
				_on_arrived()
		"exit":
			main.audio.click("walk")
			pending = t.exit
			_walk(main.nav.nav_point(t.exit.pos))
		"portal":
			main.audio.click("walk")
			pending = null
			_walk(main.nav.nav_point(t.end))
		_:
			main.audio.click("walk")
			pending = null
			_walk(t.point)


## Walk to goal, through a portal when the goal is on another part of the walk mesh.
func _walk(goal: Vector3) -> bool:
	var player = main.player
	if main.nav.reachable(player.global_position, goal):
		return player.walk_to(goal)
	if main.portals.route(goal):
		return true
	return player.walk_to(goal)


func _on_arrived() -> void:
	if pending == null:
		return
	var h = pending
	pending = null
	_hold_closed_door()
	if h.has("npc"):
		talking_npc = h.npc
		var c: Vector2 = main.rig.frame_px_of(h.npc.head() - Vector3(0, 0.5, 0))
		c.x += 360.0 / FOCUS_ZOOM
		main.rig.focus(c, FOCUS_ZOOM)
		h.npc.talk()
		_apply_highlight()
		return
	if h.has("target"):
		door_to(h)
		return
	main.player.face(SceneData.v3(h.position))
	main.audio.hotspot(h.id, SceneData.v3(h.position))
	talking = h
	var c: Vector2
	if main.compositor.has_tile(h.id):
		c = main.compositor.tile_rect(h.id).get_center()
	else:
		c = main.rig.frame_px_of(SceneData.v3(h.volume.center))
	# the dialogue column covers the right 720 canvas px: centre the object in what is left
	c.x += 360.0 / FOCUS_ZOOM
	main.rig.focus(c, FOCUS_ZOOM)
	if main.dialogue.has_look(h.id):
		main.dialogue.begin_look(h)
	else:
		main.ui.begin_conversation(null)
		main.ui.say(h.name, h.text)
	_apply_highlight()


func _on_dialogue_closed() -> void:
	pending = null
	if talking or talking_npc:
		talking = null
		talking_npc = null
		main.rig.release()
		_apply_highlight()


# ---------- exits ----------

## Walking into an exit's doorway takes it, whether it was clicked or not.
func _check_exits() -> void:
	if main.ui.busy:
		return
	var p: Vector3 = main.player.global_position
	if _exit_cooldown != null:
		if Vector2(p.x - _exit_cooldown.pos.x, p.z - _exit_cooldown.pos.z).length() > 1.2:
			_exit_cooldown = null
		return
	for e in main.nav.exits:
		var d: Vector3 = p - e.pos
		if Vector2(d.x, d.z).length() < 0.55 and absf(d.y) < 1.0:
			if pending != null and not pending.has("target") and not main.session.can_travel(e.get("target", "")):
				continue      # on the way to a person or an object: a door that opens nowhere does not stop the figure
			door_to(e)
			return


## The figure stands in the doorway of a door that opens nowhere (its target has no export) because it
## was sent to look at something or to talk, as at the stable: that door stays quiet until it has stepped away.
func _hold_closed_door() -> void:
	var p: Vector3 = main.player.global_position
	for e in main.nav.exits:
		var d: Vector3 = p - e.pos
		if Vector2(d.x, d.z).length() < 0.55 and absf(d.y) < 1.0 and not main.session.can_travel(e.get("target", "")):
			_exit_cooldown = e


## The figure stands at a door where it just arrived: it does not take the door back until it has stepped away.
func hold_exit(e) -> void:
	_exit_cooldown = e


## Takes a door ({id, pos, label, target}): into the location it names when that has an export,
## else a title card and a step back.
func door_to(e: Dictionary) -> void:
	main.player.stop()
	_exit_cooldown = e
	if e.get("target", "") != "" and main.session.travel(e.target, e.id):
		return
	var back := _step_back(e)
	await main.ui.title_card("%s — not built yet" % e.label, func():
		main.player.global_position = back
		main.player.face(back + (back - e.pos)))


## A walkable point about a metre from the exit, toward the middle of the courtyard.
func _step_back(e: Dictionary) -> Vector3:
	var to_mid: Vector3 = (main.START - e.pos)
	to_mid.y = 0.0
	return main.nav.nav_point(e.pos + to_mid.normalized() * 1.3)
