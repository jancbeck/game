## Scripted playthroughs of the whole game through its own interaction paths: clicks on people,
## hotspots and exits (interaction.act), the dialogue column's responses (ui._pick), doors between
## locations, the end of the chapter. Nothing is set in the story from outside except where the
## story is not written yet (the last scene, see `_finish`).
##
##   Godot --path game -- --playthrough-check       a window, from the title screen: New game with a
##                                                  build, the whole quest, the end of the chapter;
##                                                  a screenshot of each beat in game/shots/playthrough/
##   Godot --path game -- --release-check           the same start, then a visit to every location, with
##                                                  the time each takes to load (an exported app reads
##                                                  all of them from its data pack)
##   either flag also takes --shots-dir=<dir> for the screenshots (an exported app cannot write to res://)
##
## smoke.gd runs `run()` headless (no screenshots) after the systems check; saves and settings go to
## scratch files, never the player's. Both runs print PLAYTHROUGH lines and end with ok or the problems.
extends RefCounted

const Saves := preload("res://scripts/saves.gd")
const Settings := preload("res://scripts/settings.gd")
const Locations := preload("res://scripts/locations.gd")
const SceneData := preload("res://scripts/scene_data.gd")
const Dialogue := preload("res://scripts/dialogue.gd")
const ChapterUI := preload("res://scripts/chapter_ui.gd")

const SCRATCH_SAVES := "user://saves_playthrough"
const SCRATCH_SETTINGS := "user://settings_playthrough.json"
const BUILD := "listener"
const CHAPTER := "night_one"
const HEADLESS_SPEED := 4.0

static var started := false

var tree: SceneTree
var problems: Array[String] = []
var windowed := false
var shots_dir := "res://shots/playthrough"
var _n := 0
var _toasts := 0


## The flags of the windowed runs: starts the run once, whatever world builds first.
static func start(t: SceneTree, mode: String) -> void:
	if started:
		return
	started = true
	var c := new()
	c.windowed = DisplayServer.get_name() != "headless"
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--shots-dir="):
			c.shots_dir = arg.substr(12)
	var found: Array[String] = await c._dispatch(t, mode)
	print("PLAYTHROUGH %s" % ("ok" if found.is_empty() else "; ".join(found)))
	t.quit(0 if found.is_empty() else 1)


func _dispatch(t: SceneTree, mode: String) -> Array[String]:
	tree = t
	if mode == "playthrough":
		return await run(t)
	return await run_locations(t)


# ---------- the quest ----------

## From New game to the end of the chapter and back at the title. Returns the problems found.
func run(t: SceneTree) -> Array[String]:
	tree = t
	_scratch()
	for loc in ["cookhouse", "tower"]:
		if not Locations.exists(m().data.config, loc):
			print("PLAYTHROUGH skipped: no export of %s" % loc)
			_clean()
			return problems
	ChapterUI.fade_s = 0.4
	ChapterUI.dwell_s = 0.8
	Dialogue.chapter_read_s = 1.0
	if not windowed:
		Engine.time_scale = HEADLESS_SPEED       # the figure walks the yard in a few seconds
	await _new_game()
	await _skip_intro()
	await _shot("yard_start")

	# the gate: Marl offers the task
	await _talk("marl", ["anything I can do", "Leave"], "marl_greeting")
	_expect(m().quest.get_flag("rider") == 1 and m().journal.has("rider"), "Marl's offer did not start the task")
	# the stable and the bell, as hotspots
	await _look("stable", ["Pick it up"], "stable")
	_expect(m().inventory.has("broken_seal") and m().quest.get_flag("rider") == 2, "the seal was not found in the stable")
	await _look("bell", ["Untie it"], "bell")
	_expect(m().inventory.has("greasy_rag") and m().quest.get_flag("rider") == 3, "the linen was not found at the bell")
	# the cookhouse through its door: Hedda
	await _door("cookhouse", "cookhouse")
	await _shot("cookhouse")
	await _talk("hedda", ["Hold up the greasy linen", "Why tie", "Leave"], "hedda")
	_expect(m().quest.get_flag("rider") == 4, "Hedda did not confess")
	await _door("courtyard", "courtyard")
	_expect(m().player.global_position.distance_to(_exit("cookhouse").pos) < 3.0, "the figure did not come out of the cookhouse door")
	# Tam on the landing of the north-west tower (through the portal): wake him, ask about the seal,
	# then try the empathy check; if it fails the letter is asked for plainly. Either way the quest goes on.
	await _talk("tam", ["Wake him", "Then who broke", "I'll make sure", "?Give me the letter"], "tam")
	var q = m().quest
	for key in m().skills.rolls:
		print("PLAYTHROUGH roll %s: %s" % [key, "passed" if m().skills.rolls[key].success else "failed"])
	_expect(m().inventory.has("letter") and q.get_flag("rider") == 5 and q.get_flag("tam_woken") and q.get_flag("knows_ford") and q.get_flag("tam_wants_commander"), "Tam did not give the letter")
	# back to Marl: the letter goes to the commander
	await _talk("marl", ["commander myself"], "marl_finale")
	_expect(m().quest.get_flag("letter_outcome") == "commander" and m().quest.get_flag("rider") == 6 and m().inventory.has("letter"), "Marl's finale did not let the letter go on")
	# the tower: by its door in the south parapet when the export has one, else by the travel API
	await _to_tower()
	await _shot("tower")
	await _talk("commander", ["Give him the letter", "At the ford", "only lost"], "commander")
	q = m().quest
	_expect(q.get_flag("letter_delivered") and q.get_flag("player_claim") == "lost" and m().journal.has("ferryman") and not m().inventory.has("letter"), "the commander's scene did not run through")
	await _door("courtyard", "courtyard")
	m().sheet_ui.open("journal")
	await _shot("journal")
	m().sheet_ui.close()
	await _finish()
	_clean()
	return problems


## The last scene: Marl and the horse. While the story has no such scene, the chapter is ended by
## the external the story would call.
func _finish() -> void:
	await _talk("marl", ["?horse"], "marl_horse")
	if not m().chapter.active:
		print("PLAYTHROUGH the story has no horse scene yet: end_chapter(\"%s\") is called directly" % CHAPTER)
		m().dialogue.ext_end_chapter(CHAPTER)
	_expect(await _within(func(): return m().chapter.page == "card", 20.0), "the chapter did not end in a card")
	await tree.create_timer(0.5).timeout
	await _shot("chapter_card")
	m().chapter._on_continue()
	_expect(await _within(func(): return m().chapter.page == "summary", 6.0), "the card did not lead to the page of choices")
	await tree.create_timer(0.3).timeout
	await _shot("chapter_choices")
	var text := _texts(m().chapter.summary_page)
	_expect("You gave" in text or "promise to Tam" in text or "You kept" in text, "the page of choices does not say what happened to the letter")
	m().chapter._on_leave()
	_expect(await _within(func(): return m().menu.is_open() and m().menu.screen == "title", 20.0), "the chapter did not lead back to the title")
	await tree.create_timer(2.5).timeout
	await _shot("title_after")
	var cont := _button("Continue")
	_expect(cont != null and cont.disabled, "the title still offers Continue at the end of the story")


# ---------- the locations of the game ----------

## New game, then every location in turn by travel; prints how long each takes to appear. For the
## exported app: every location must load from its data pack.
func run_locations(t: SceneTree) -> Array[String]:
	tree = t
	_scratch()
	await _new_game()
	await _skip_intro()
	var start: String = m().session.location
	print("PLAYTHROUGH data %s: release data %s, %d MB video memory" % [m().data.data_path, "on" if SceneData.release_active() else "off", _vram()])
	await _shot("location_" + start)
	var names: Array[String] = []
	for d in DirAccess.get_directories_at("res://locations"):
		names.append(d)
	names.sort()
	names.append(start)
	for name in names:
		if not Locations.exists(m().data.config, name):
			_expect(false, "no data for the location %s" % name)
			continue
		var t0 := Time.get_ticks_msec()
		_expect(m().session.travel(name, ""), "the way to %s is refused" % name)
		await _arrive(name)
		var ms := Time.get_ticks_msec() - t0
		var mm = m()
		var tile: String = mm.data.hotspots[0].id if not mm.data.hotspots.is_empty() else ""
		var t1 := Time.get_ticks_msec()
		var tile_ms := -1
		if tile != "" and mm.compositor.has_tile(tile):
			mm.compositor.request_tile(tile)
			if await _within(func(): return m().compositor.tile_ready(tile), 30.0):
				tile_ms = Time.get_ticks_msec() - t1
		var layers: String = mm.data.scene.layers.base
		print("PLAYTHROUGH %s: on screen %d ms after the door (with the fades), data %s, base layer from %s, tile %s ready in %d ms, %d hotspots, %d people, %d MB video memory" % [
			name, ms, mm.data.data_path, "release data" if SceneData.uses_release(layers) else "raw EXR", tile, tile_ms,
			mm.data.hotspots.size(), mm.npcs.size(), _vram()])
		_expect(mm.data.hotspots.size() > 0 and mm.compositor.has_tile(tile), "%s loaded without hotspots or tiles" % name)
		await _shot("location_" + name)
	_clean()
	return problems


# ---------- the means ----------

func _scratch() -> void:
	Saves.dir = SCRATCH_SAVES
	Settings.path = SCRATCH_SETTINGS
	Settings.load_file()
	Settings.set_value("text_speed", "instant")
	Settings.set_value("auto_advance", true)
	if windowed:
		DirAccess.make_dir_recursive_absolute(shots_dir if shots_dir.begins_with("/") else ProjectSettings.globalize_path(shots_dir))


func _clean() -> void:
	for slot in Saves.slot_ids():
		Saves.delete(slot)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SCRATCH_SAVES))
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SCRATCH_SETTINGS))
	Saves.dir = "user://saves"
	Settings.path = "user://settings.json"
	Settings.load_file()
	Engine.time_scale = 1.0
	ChapterUI.fade_s = 1.4
	ChapterUI.dwell_s = 2.4
	Dialogue.chapter_read_s = 2.5


## The world that is current (the node of main.gd; a door or a load replaces it).
func m() -> Node:
	for c in tree.root.get_children():
		if c.get("session") != null and c.get("data") != null:
			return c
	return null


func _expect(ok: bool, what: String) -> void:
	if not ok:
		problems.append("playthrough: " + what)
		print("PLAYTHROUGH FAILED: %s" % what)


func _until(cond: Callable, frames := 600) -> bool:
	for i in frames:
		if cond.call():
			return true
		await tree.process_frame
	return cond.call()


func _within(cond: Callable, seconds: float) -> bool:
	var t0 := Time.get_ticks_msec()
	while Time.get_ticks_msec() - t0 < seconds * 1000.0:
		if cond.call():
			return true
		await tree.process_frame
	return cond.call()


## A screenshot of the window as the player sees it (windowed runs only).
func _shot(name: String) -> void:
	if not windowed:
		return
	await tree.create_timer(0.35).timeout
	await RenderingServer.frame_post_draw
	_n += 1
	var path := "%s/%02d_%s.png" % [shots_dir, _n, name]
	tree.root.get_viewport().get_texture().get_image().save_png(path if path.begins_with("/") else ProjectSettings.globalize_path(path))
	print("PLAYTHROUGH shot %s" % path)


func _vram() -> int:
	return int(Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0)


func _texts(n: Node) -> String:
	var out: String = n.text + "\n" if (n is Label or n is RichTextLabel) else ""
	for c in n.get_children():
		out += _texts(c)
	return out


func _button(text: String) -> Button:
	for c in m().menu.column.get_children():
		if c is Button and c.text == text:
			return c
	return null


## New game with the build: through the title screen when it is up, else straight into the skills.
func _new_game() -> void:
	await _until(func(): return m() != null and m().session.placed, 900)
	var mm = m()
	if mm.menu.is_open() and mm.menu.mode == "title":
		await tree.create_timer(2.0).timeout
		await _shot("title")
		mm.menu._show("new_game")
		await tree.create_timer(0.4).timeout      # the first build takes focus, which picks it
		mm.menu._pick_build(BUILD)
		await tree.create_timer(0.4).timeout
		await _shot("new_game")
		mm.menu._begin_game()
		_expect(mm.skills.archetype == BUILD, "the build did not reach the skills")
		await _within(func(): return not m().menu.is_open(), 6.0)
	else:
		mm.begin_game(BUILD, mm.session.archetypes.find(BUILD).skills.duplicate())


## The intro shows the wide view for a moment, then it is cut short.
func _skip_intro() -> void:
	await tree.create_timer(1.5 if windowed else 0.2).timeout
	if windowed:
		await _shot("intro")
	if m().rig.in_intro():
		m().rig._intro_t = m().rig.intro_s
	await _until(func(): return not m().rig.in_intro(), 120)


## Waits for the world of `location` to stand: built, figure placed, faded in.
func _arrive(location: String) -> void:
	var ok := await _within(func():
		var n = m()
		return n != null and n.session.location == location and n.session.placed and not n.session.traveling and n.ui.fade.modulate.a < 0.02 and not n.ui.busy, 60.0)
	_expect(ok, "the world of %s did not come up" % location)
	await tree.create_timer(0.3).timeout


func _exit(id: String) -> Dictionary:
	for e in m().nav.exits:
		if e.id == id:
			return e
	return {}


## Walks to a door of this location (as a click on it does) and through it.
func _door(id: String, into: String) -> void:
	var e := _exit(id)
	_expect(not e.is_empty(), "no door %s in %s" % [id, m().session.location])
	if e.is_empty():
		return
	m().interaction.act({kind = "exit", exit = e, point = e.pos})
	await _arrive(into)


func _to_tower() -> void:
	var e := _exit("tower")
	if not e.is_empty():
		await _door("tower", "tower")
	else:
		print("PLAYTHROUGH the courtyard export has no door to the tower yet: travel to it")
		m().session.travel("tower", "tower")
		await _arrive("tower")


## Clicks on a person: the figure walks to them (through a door when it must) and the conversation opens.
func _talk(id: String, picks: Array, shot: String) -> void:
	var n = m().npc_by_id(id)
	_expect(n != null, "%s is not in %s" % [id, m().session.location])
	if n == null:
		return
	m().interaction.act({kind = "npc", npc = n, point = n.figure.global_position})
	_expect(await _within(func(): return m().ui.is_open(), 90.0), "the figure did not reach %s" % id)
	await _converse(picks, shot)


## Clicks on an object: the look text opens at its stand point.
func _look(id: String, picks: Array, shot: String) -> void:
	var hs: Array = m().data.hotspots.filter(func(h): return h.id == id)
	_expect(not hs.is_empty(), "no hotspot %s" % id)
	if hs.is_empty():
		return
	m().interaction.act({kind = "hotspot", hotspot = hs[0], point = SceneData.v3(hs[0].position), walkable = false})
	_expect(await _within(func(): return m().ui.is_open(), 90.0), "the figure did not reach the %s" % id)
	await _converse(picks, shot)


## Plays the open conversation: at each set of responses it takes the first that contains the next
## of `picks` (a "?" in front: when there is none, leave), and goes on until the column closes. The
## screenshot is of the first set of responses.
func _converse(picks: Array, shot: String) -> void:
	var step := 0
	var shot_done := shot == ""
	var deadline := Time.get_ticks_msec() + 120000
	while Time.get_ticks_msec() < deadline:
		var ui = m().ui
		if not ui.is_open():
			return
		if windowed and _toasts < 2 and m().inventory_ui.notice.modulate.a > 0.8:
			_toasts += 1
			await _shot("notice")
		if ui.option.visible and not ui.suspended:
			if not shot_done:
				shot_done = true
				await _shot(shot)
				continue
			var want: String = picks[step] if step < picks.size() else "Leave"
			var optional := want.begins_with("?")
			var i := _find(ui, want.trim_prefix("?"))
			if i < 0:
				if not optional:
					_expect(false, "no response '%s' among %s" % [want, ui.choices.map(func(c): return c if c is String else c.text)])
				i = _find(ui, "Leave")
				step = picks.size()
				if i < 0:
					i = 0
			else:
				step += 1
			ui._pick(i)
		else:
			m().dialogue.skip()
		await tree.process_frame
	_expect(false, "a conversation did not end")


## The first response that is not locked and holds `text`; with no responses (a look text) 0.
func _find(ui, text: String) -> int:
	if ui.choices.is_empty():
		return 0
	for i in ui.choices.size():
		var c = ui.choices[i]
		var label: String = c if c is String else c.text
		if text in label and not ui.is_locked(i):
			return i
	return -1
