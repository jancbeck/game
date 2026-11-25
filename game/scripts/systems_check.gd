## The headless check of the player-facing systems, run by smoke.gd after the game has started:
## the story advances on a choice, a hotspot runs its look knot, passive and active skill checks
## and the journal behave (on the fixture story tests/checks.ink), the builds of a new game reach
## the skills, the dialogue column follows and reveals its lines and waits for the player when
## auto-advance is off, a skill's clip ducks the ambience, settings persist, a slot save
## round-trips position, satchel, flags, skills, rolls and journal, the pad walks and selects, a
## change of location keeps the state and puts the figure at the matching door, a missing location
## fails without leaving the world, a chapter ends in a card and a page of choices that name what the
## story did, the save made there loads to the card again, and the title screen comes back.
##
## Returns the problems found. It never touches the player's own saves or settings: Saves.dir and
## Settings.path point at scratch files.
extends RefCounted

const Session := preload("res://scripts/session.gd")
const Locations := preload("res://scripts/locations.gd")
const Cursor := preload("res://scripts/cursor.gd")
const Story := preload("res://scripts/story.gd")
const Skills := preload("res://scripts/skills.gd")
const Ui := preload("res://scripts/ui.gd")
const Dialogue := preload("res://scripts/dialogue.gd")
const Saves := preload("res://scripts/saves.gd")
const Settings := preload("res://scripts/settings.gd")
const Music := preload("res://scripts/music.gd")
const Chapters := preload("res://scripts/chapters.gd")
const ChapterUI := preload("res://scripts/chapter_ui.gd")

const SCRATCH_SAVES := "user://saves_check"
const SCRATCH_SETTINGS := "user://settings_check.json"
const SCRATCH_CLIPS := "user://skill_check"

var tree: SceneTree
var problems: Array[String] = []


func run(t: SceneTree) -> Array[String]:
	tree = t
	Saves.dir = SCRATCH_SAVES
	Settings.path = SCRATCH_SETTINGS
	_scrub()
	Settings.load_file()
	Settings.set_value("text_speed", "instant")
	Session.fade_s = 0.0
	await _frames(2)
	await _story_and_dialogue()
	_quest()
	await _skills_and_checks()
	await _builds()
	await _column()
	await _voices()
	_settings()
	await _panels()
	await _pad()
	await _save_round_trip()
	await _locations()
	await _chapter()
	await _title()
	_clean()
	return problems


## Removes what the checks wrote and puts the real paths back.
func _clean() -> void:
	_scrub()
	Locations.overrides.clear()
	Saves.dir = "user://saves"
	Settings.path = "user://settings.json"
	Settings.load_file()
	Dialogue.skill_dir = "res://assets/skills"


## The scratch files, also those a crashed run left behind.
func _scrub() -> void:
	for slot in Saves.slot_ids():
		Saves.delete(slot)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SCRATCH_SAVES))
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SCRATCH_SETTINGS))
	if DirAccess.dir_exists_absolute(SCRATCH_CLIPS):
		for f in DirAccess.get_files_at(SCRATCH_CLIPS):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(SCRATCH_CLIPS + "/" + f))
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SCRATCH_CLIPS))


func main_node() -> Node:
	for c in tree.root.get_children():
		if c.get("session") != null and c.get("data") != null:
			return c
	return null


func expect(ok: bool, what: String) -> void:
	if not ok:
		problems.append("systems: " + what)


func _frames(n: int) -> void:
	for i in n:
		await tree.process_frame


func _until(cond: Callable, max_frames := 240) -> bool:
	for i in max_frames:
		if cond.call():
			return true
		await tree.process_frame
	return cond.call()


## Waits up to `seconds` of real time (the dialogue plays its lines on a timer).
func _within(cond: Callable, seconds := 6.0) -> bool:
	var t0 := Time.get_ticks_msec()
	while Time.get_ticks_msec() - t0 < seconds * 1000.0:
		if cond.call():
			return true
		await tree.process_frame
	return cond.call()


# ---------- the quest, played through on the story alone ----------

## Runs `knot`, taking at each choice the first option containing the next of `picks`; returns
## the text it printed. Stops when the story ends or no option matches.
func _play(m: Node, knot: String, picks: Array) -> String:
	m.story.goto(knot)
	var out := ""
	var i := 0
	while true:
		while m.story.can_continue():
			out += m.story.next_line().text + "\n"
		var opts: Array = m.story.choices()
		if opts.is_empty() or i >= picks.size():
			break
		var k := opts.find_custom(func(o): return picks[i] in o)
		if k < 0:
			problems.append("systems: quest: no option '%s' in %s" % [picks[i], opts])
			break
		m.story.choose(k)
		i += 1
	return out


## "The rider nobody rang for" from Marl's offer to the letter, then restores the state.
func _quest() -> void:
	var m := main_node()
	if m == null or not m.story.ok():
		return
	var saved: String = m.story.state_json()
	var had: Array = ["broken_seal", "greasy_rag", "letter"].filter(func(i): return m.inventory.has(i))
	_play(m, "talk_marl", ["anything I can do", "Leave"])
	expect(m.story.get_var("rider") == 1, "quest: Marl's offer did not start it")
	_play(m, "look_stable", ["Pick it up"])
	expect(m.inventory.has("broken_seal"), "quest: the seal is not in the satchel")
	_play(m, "look_bell", ["Untie it"])
	expect(m.inventory.has("greasy_rag") and m.story.get_var("rider") == 3, "quest: the linen was not found")
	var h := _play(m, "talk_hedda", ["Hold up the greasy linen", "Why tie", "Leave"])
	expect("Tam" in h and m.story.get_var("rider") == 4, "quest: Hedda did not confess")
	_play(m, "talk_tam", ["Wake him", "Give me the letter"])
	expect(m.inventory.has("letter") and m.story.get_var("rider") == 5, "quest: the letter was not taken")
	expect(m.story.get_var("tam_wants_commander"), "quest: Tam did not ask for the commander")
	var f := _play(m, "talk_marl", ["Give him the letter"])
	expect("Recalled" in f and not m.inventory.has("letter") and m.story.get_var("rider") == 6, "quest: Marl's ending did not run")
	var c := _play(m, "talk_commander", ["I don't know"])
	expect("Three waves" in c and m.story.get_var("letter_delivered"), "quest: the commander's scene did not run after Marl's ending")
	m.story.restore(saved)
	for id in ["broken_seal", "greasy_rag", "letter"]:
		if m.inventory.has(id) and not id in had:
			m.inventory.remove(id)


# ---------- skills, checks and the journal, on the fixture story ----------

## A second dialogue on tests/checks.ink, using the game's column, skills and journal.
static func fixture_dialogue(m: Node) -> Node:
	var s := Story.new()
	if not s.load_file("tests/checks.json"):
		return null
	var d := Dialogue.new()
	m.add_child(d)
	d.setup(m, s)
	return d


## Runs a knot of the fixture to its options; returns the log (BBCode source).
func _run(m: Node, d: Node, knot: String) -> String:
	m.ui.begin_conversation(null)
	d._begin(knot, "", "Test")
	await _within(func(): return m.ui.option.visible)
	return m.ui.log_text.text


func _picked(m: Node, i: int) -> void:
	m.ui._pick(i)
	await _frames(2)
	await _within(func(): return m.ui.option.visible)


func _skills_and_checks() -> void:
	var m := main_node()
	var sk = m.skills
	var d := fixture_dialogue(m)
	expect(d != null, "tests/checks.json did not load (run scripts/ink.py)")
	if d == null:
		return
	var saved := {skills = sk.to_dict(), journal = m.journal.to_dict()}
	expect(sk.defs.size() == 6 and sk.defs.all(func(s): return int(s.value) >= 1 and int(s.value) <= 5), "data/skills.json: six skills starting at 1 to 5")
	expect(sk.parse_dc("Challenging") == 12 and sk.difficulty_name(18) == "Impossible", "difficulty names do not match the table")
	# two sixes always succeed, two ones always fail
	expect(is_equal_approx(Skills.chance(0, 99), 1.0 / 36.0) and is_equal_approx(Skills.chance(9, 2), 35.0 / 36.0), "double six / double one do not decide a check")

	# passive: the line is there when skill + 6 reaches the number, else not
	sk.set_value("perception", 3)
	sk.set_value("stonework", 3)
	var low := await _run(m, d, "passives")
	expect("Everyone hears" in low and not "boot print" in low and not "hard winter" in low, "passive lines showed below their number")
	m.ui.close()
	sk.set_value("perception", 4)
	sk.set_value("stonework", 6)
	var high := await _run(m, d, "passives")
	expect("boot print" in high and "Medium: Success" in high and "hard winter" in high, "passive lines did not show at their number")
	m.ui.close()

	# active: two checks that fail on their first throw, found by seed
	var white := Dialogue.check_key("checks", "authority", 18, "white")
	var red := Dialogue.check_key("checks", "authority", 18, "red")
	sk.set_value("authority", 2)
	for seed in 500:
		sk.dice_seed = seed
		sk.rolls.clear()
		if not sk.roll(white, "authority", 18, "white").success and not sk.roll(red, "authority", 18, "red").success:
			break
	sk.rolls.clear()
	await _run(m, d, "checks")
	var opt: Dictionary = m.ui.choices[0] if m.ui.choices[0] is Dictionary else {}
	expect("Impossible 18" in opt.get("tag", "") and "3%" in opt.get("tag", "") and not opt.get("locked", true), "a check option does not show its difficulty and chance")
	expect(m.ui.choices[1].tag_color != opt.tag_color, "a red check is drawn like a white one")
	await _picked(m, 0)
	expect("Failure" in m.ui.log_text.text and "He does not" in m.ui.log_text.text, "a failed roll is not in the log")
	expect(m.ui.is_locked(0) and not m.ui.is_locked(1), "a failed white check is not locked until it may be retried")
	m.ui._pick(0)
	await _frames(3)
	expect(sk.rolls[white].attempts == 1, "a locked option was rolled again")
	await _picked(m, 1)
	expect(m.ui.is_locked(1), "a failed red check is not locked")
	m.ui.move_option(1)
	expect(m.ui._hot == 2, "the pad highlight does not skip locked options")
	var kept: Dictionary = sk.rolls[red].duplicate()
	sk.set_value("authority", 5)
	expect(sk.state_of(red, "authority", 18).locked and sk.roll(red, "authority", 18, "red").total == kept.total, "a red check was made again")
	# white: locked until the skill rises or the flag the check names is set
	sk.set_value("authority", 2)
	expect(sk.state_of(white, "authority", 18).locked and not sk.state_of(white, "authority", 18, true).locked, "the flag of a white check does not unlock it")
	sk.set_value("authority", 3)
	m.ui.close()
	await _run(m, d, "checks")
	expect(not m.ui.is_locked(0) and m.ui.is_locked(1), "a white check is still locked after the skill rose")
	await _picked(m, 0)
	expect(sk.rolls[white].attempts == 2, "a white check was not made again after the skill rose")
	# a result survives the save file
	var again := Skills.new()
	again.load_defs("data/skills.json")
	again.from_dict(JSON.parse_string(JSON.stringify(sk.to_dict())))
	expect(not again.roll(red, "authority", 18, "red").fresh and again.roll(red, "authority", 18, "red").total == kept.total, "a roll was lost in the save")
	m.ui.close()

	# the journal follows the story's tags, also on a line without text
	await _run(m, d, "journal_demo")
	expect(m.journal.has("test_task") and "Find the rider" in m.journal.entries.test_task.text, "journal: the task was not opened")
	await _picked(m, 0)
	expect("sleeps in the tower" in m.journal.entries.test_task.text and not m.journal.is_done("test_task"), "journal: the text was not replaced")
	await _picked(m, 0)
	expect(m.journal.is_done("test_task"), "journal: the task was not closed")
	m.ui.close()

	# skill_value and skill_add are what the story sees
	sk.set_value("logic", 3)
	var v := await _run(m, d, "values")
	expect("Dull" in v and sk.value("logic") == 4, "skill_value / skill_add did not reach the skills")
	m.ui.close()

	d.queue_free()
	sk.from_dict(saved.skills)
	m.journal.from_dict(saved.journal)


## The sheet and the journal open from their keys, show the state, and keep the column quiet.
func _panels() -> void:
	var m := main_node()
	m.journal.update("panel_task", "Count the spears.")
	_key(KEY_C)
	await _frames(2)
	expect(m.sheet_ui.is_open() and m.sheet_ui.mode == "sheet" and m.ui.suspended, "C did not open the character sheet")
	expect(m.sheet_ui._rows[0].value.text == str(m.skills.value(m.skills.defs[0].id)), "the sheet does not show the skill value")
	_key(KEY_J)
	await _frames(2)
	expect(m.sheet_ui.mode == "journal" and "Count the spears" in m.sheet_ui.journal_text.text, "J did not switch to the journal")
	_key(KEY_ESCAPE)
	await _frames(2)
	expect(not m.sheet_ui.is_open() and not m.ui.suspended, "Escape did not close the journal")
	m.journal.entries.erase("panel_task")


func _key(code: int) -> void:
	for down in [true, false]:
		var e := InputEventKey.new()
		e.keycode = code
		e.pressed = down
		Input.parse_input_event(e)


# ---------- story, dialogue, hotspots ----------

func _story_and_dialogue() -> void:
	var m = main_node()
	expect(m.story.ok(), "the Ink story did not load (run Godot --headless --path game --import once)")
	if not m.story.ok():
		return
	for ext in ["give_item", "take_item", "has_item", "set_flag", "get_flag", "play_line", "roll", "skill_value", "skill_add", "end_chapter"]:
		expect(m.story.ink._externals.has(ext), "external %s is not bound" % ext)
	# a conversation: the greeting is voiced by its clip, a choice advances to the next knot
	var marl = m.npc_by_id("marl")
	expect(marl != null, "Marl is not in the courtyard")
	if marl == null:
		return
	marl.talk()
	# skip the voiced lines as a player can (headless frames run faster than the clips)
	expect(await _until(func(): m.dialogue.skip(); return m.ui.option.visible and m.ui.choices.size() == 5), "Marl's greeting did not offer 5 responses")
	expect(m.quest.flag("met_marl"), "the story variable met_marl did not reach main.quest")
	m.ui._pick(0)
	expect(await _until(func(): m.dialogue.skip(); return "Thirty-one winters" in m.ui.log_text.text), "choosing 'Who are you?' did not advance")
	expect("Sergeant Marl" in m.ui.log_text.text, "Marl's second line is not in the log")
	m.ui.close()
	# a hotspot with a look knot runs it; one without shows its static text
	var bell: Dictionary = m.data.hotspots.filter(func(h): return h.id == "bell")[0]
	expect(m.dialogue.has_look("bell"), "the story has no look_bell knot")
	m.interaction.pending = bell
	m.interaction._on_arrived()
	expect(await _until(func(): return m.quest.flag("bell_looked")), "look_bell did not set bell_looked")
	expect(await _until(func(): return m.ui.option.visible), "look_bell did not end in its [Leave.]")
	m.ui.close()
	var gate: Dictionary = m.data.hotspots.filter(func(h): return not m.dialogue.has_look(h.id))[0]
	m.interaction.pending = gate
	m.interaction._on_arrived()
	expect(gate.text.left(20) in m.ui.log_text.text, "a hotspot without a look knot lost its static text")
	m.ui.close()
	# the pointer
	var a := Cursor.make(false)
	var b := Cursor.make(true)
	var inked := 0
	for p in Rect2i(2, 33, 8, 8).get_area():
		inked += 1 if a.get_pixel(2 + p % 8, 33 + p / 8).a > 0.5 else 0
	expect(inked > 8 and a.get_pixel(41, 41).a < 0.1, "the cursor is not drawn around its nib")
	expect(a.get_data() != b.get_data(), "the hover cursor equals the plain one")


# ---------- pad ----------

func _joy_axis(axis: int, value: float) -> void:
	var e := InputEventJoypadMotion.new()
	e.axis = axis
	e.axis_value = value
	Input.parse_input_event(e)


func _joy_button(button: int, pressed: bool) -> void:
	var e := InputEventJoypadButton.new()
	e.button_index = button
	e.pressed = pressed
	Input.parse_input_event(e)


func _pad() -> void:
	var m = main_node()
	m.player.global_position = m.nav.nav_point(Vector3(-2.0, 0.0, 2.2))
	var before: Vector3 = m.player.global_position
	_joy_axis(JOY_AXIS_LEFT_Y, -1.0)
	await tree.create_timer(0.8).timeout
	expect(m.pad.driving and m.pad.active, "the left stick does not walk the figure")
	var moved: Vector3 = m.player.global_position - before
	expect(moved.length() > 0.5 and moved.z < -0.3, "stick up did not walk up the screen (moved %s)" % moved)
	_joy_axis(JOY_AXIS_LEFT_Y, 0.0)
	await tree.create_timer(0.15).timeout
	expect(not m.pad.driving and not m.player.walking, "the figure keeps walking after the stick is released")
	_joy_button(JOY_BUTTON_DPAD_RIGHT, true)
	_joy_button(JOY_BUTTON_DPAD_RIGHT, false)
	await _frames(3)
	var first = m.interaction.selected
	expect(first != null and m.interaction.hovered == first, "the D-pad did not select the nearest thing")
	_joy_button(JOY_BUTTON_DPAD_RIGHT, true)
	_joy_button(JOY_BUTTON_DPAD_RIGHT, false)
	await _frames(3)
	expect(m.interaction.selected != null and not m.pad._same(m.interaction.selected, first), "the D-pad did not move on to another thing")
	_joy_button(JOY_BUTTON_A, true)
	_joy_button(JOY_BUTTON_A, false)
	await _frames(3)
	expect(m.interaction.pending != null or m.ui.is_open(), "A did not interact with the selection")
	m.player.stop()
	m.interaction.pending = null
	m.ui.close()
	m.pad.use_pad(false)
	m.interaction.set_selected(null)
	await _frames(2)


# ---------- builds, the column, voices, settings ----------

## A build lands in the skills and the save; the custom points cannot be overspent; Begin plays the game.
func _builds() -> void:
	var m := main_node()
	var arch = m.session.archetypes
	var sk = m.skills
	expect(arch.defs.size() >= 3, "data/archetypes.json offers fewer than three builds")
	for d in arch.defs:
		expect(arch.valid(d.skills), "archetype %s: %s" % [d.id, "; ".join(arch.problems(d.skills))])
	var before: Dictionary = sk.to_dict()
	var pick: Dictionary = arch.defs[0]
	sk.apply_build(pick.id, pick.skills)
	expect(sk.ids().all(func(id): return sk.value(id) == int(pick.skills[id])) and sk.archetype == pick.id, "a build did not reach the skills")
	var again := Skills.new()
	again.load_defs("data/skills.json")
	again.from_dict(JSON.parse_string(JSON.stringify(sk.to_dict())))
	expect(again.archetype == pick.id and again.value("logic") == int(pick.skills.logic), "a build was lost in the save")
	# the custom screen: every slider to the top spends the twelve points and no more
	m.menu.open_title()
	m.menu._show("new_game")
	m.menu._pick_build("custom")
	expect(m.menu._begin.disabled, "Begin is open before the points are spent")
	for id in sk.ids():
		m.menu._sliders[id].value = 5
	expect(arch.left(m.menu.build) == 0 and arch.valid(m.menu.build) and not m.menu._begin.disabled, "the custom build overspent or Begin stayed shut")
	m.menu._begin_game()
	expect(sk.archetype == "custom" and sk.value("perception") == 5 and sk.value("composure") == 1, "Begin did not give the custom build to the skills")
	await _frames(2)
	# every screen builds and has something to focus
	m.menu.close()
	m.menu.open_title()
	m.menu.save_slot = "slot_1"
	for id in ["settings", "save", "save_name", "confirm_title", "confirm_quit", "load", "new_game"]:
		m.menu._show(id)
		expect(m.menu.panel.visible and not m.menu.column.visible and m.menu._first != null, "the %s screen did not build" % id)
	# the settings screen: a row steps its setting, a slider moves a volume and its bus
	m.menu._show("settings")
	var rows: Array = m.menu.panel.find_children("*", "Button", true, false)
	var sliders: Array = m.menu.panel.find_children("*", "HSlider", true, false)
	expect(rows.size() == 5 and sliders.size() == 5, "the settings screen is missing rows (%d buttons, %d sliders)" % [rows.size(), sliders.size()])
	rows[0].pressed.emit()
	expect(Settings.get_value("text_speed") == "fast", "a settings row did not step to its next value")
	Settings.set_value("text_speed", "instant")
	sliders[0].value = 50
	expect(is_equal_approx(Settings.volume("master"), 0.5) and absf(AudioServer.get_bus_volume_db(0) - linear_to_db(0.5)) < 0.1, "the master slider did not reach the Master bus")
	sliders[0].value = 100
	sliders[2].value = 50
	expect(absf(AudioServer.get_bus_volume_db(AudioServer.get_bus_index("Ambience")) - m.audio._zoom_db - m.audio.duck_db - linear_to_db(0.5)) < 0.1, "the ambience slider did not reach the Ambience bus")
	sliders[2].value = 100
	# the title music starts on its own bus and fades once a game begins
	Music.title(m)
	expect(Music.playing() and AudioServer.get_bus_index("Music") >= 0, "the title music did not start")
	Music.fade_out()
	expect(Music._tween.is_valid(), "the title music did not fade out")
	Music._player.stop()
	m.menu.close()
	m.menu.open_pause()
	expect(m.menu.mode == "pause" and m.menu.column.visible and m.menu.column.get_child_count() >= 6, "the pause menu did not open")
	m.menu.close()
	sk.from_dict(before)


## The log follows its newest line, the newest line appears at the text speed, and with
## auto-advance off every line waits for the player.
func _column() -> void:
	var m := main_node()
	var ui = m.ui
	ui.begin_conversation(null)
	for i in 40:
		ui.say("Marl", "Line %d of a long talk, long enough to wrap across the column and take some room in it." % i)
	var bar: VScrollBar = ui.log_text.get_v_scroll_bar()
	expect(await _within(func(): return bar.max_value > bar.page + 10.0 and ui.at_end(), 3.0), "a long log does not scroll to its newest line")
	expect(Ui.faded(Ui.INK, 0).v > Ui.faded(Ui.INK, 3).v + 0.1, "older lines are not dimmer than the newest")
	Settings.set_value("text_speed", "slow")
	ui.say("Marl", "A line that appears letter by letter.")
	expect(ui.revealing() and ui.log_text.visible_characters < ui.log_text.get_total_character_count(), "the newest line did not start hidden")
	ui.finish_reveal()
	expect(not ui.revealing() and ui.log_text.visible_characters == -1, "finish_reveal left text hidden")
	Settings.set_value("text_speed", "instant")
	ui.close()
	# auto-advance off: the first line shows, the next two come one press each, then the responses
	var sk = m.skills
	var kept: Dictionary = sk.to_dict()
	sk.set_value("empathy", 5)
	sk.set_value("stonework", 5)
	Settings.set_value("auto_advance", false)
	var d := fixture_dialogue(m)
	ui.begin_conversation(null)
	d._begin("showcase", "marl", "")
	expect(await _within(func(): return "wipes his hands" in ui.log_text.text, 3.0), "the first line did not show")
	await tree.create_timer(0.8).timeout
	expect(not "lying about" in ui.log_text.text and not ui.option.visible, "the second line came without the player's go-ahead")
	d.advance()
	expect(await _within(func(): return "lying about" in ui.log_text.text, 3.0), "advance did not bring the next line")
	d.advance()
	expect(await _within(func(): return "older than his oath" in ui.log_text.text, 3.0), "advance did not bring the line after")
	expect(await _within(func(): return ui.option.visible, 3.0), "the responses did not follow the last line")
	Settings.set_value("auto_advance", true)
	ui.close()
	d.queue_free()
	sk.from_dict(kept)


## `# line:<clip>` on a skill plays assets/skills/<clip>.wav and ducks the ambience for as long as it lasts.
func _voices() -> void:
	var m := main_node()
	DirAccess.make_dir_recursive_absolute(SCRATCH_CLIPS)
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = 8000
	var pcm := PackedByteArray()
	pcm.resize(8000 * 2 * 6 / 10)
	wav.data = pcm
	wav.save_to_wav(SCRATCH_CLIPS + "/ping.wav")
	Dialogue.skill_dir = SCRATCH_CLIPS
	expect(m.dialogue._start_skill_voice("nothing") == 0.0 and not m.dialogue.voice_active(), "a missing skill clip was played")
	var length: float = m.dialogue._start_skill_voice("ping")
	expect(length > 0.5 and m.dialogue.voice_active(), "a skill's clip did not play")
	expect(await _within(func(): return m.audio.duck_db < -4.0, 2.0), "the ambience did not duck under a skill's voice")
	expect(await _within(func(): return not m.dialogue.voice_active() and m.audio.duck_db > -0.5, 4.0), "the ambience did not come back after the voice")
	expect(AudioServer.get_bus_index("Voice") >= 0, "there is no Voice bus")


## Settings written to their file come back, land on the buses, and refuse a wrong kind of value.
func _settings() -> void:
	Settings.set_value("voice", 0.4)
	Settings.set_value("text_speed", "slow")
	Settings.set_value("auto_advance", false)
	Settings.set_value("hints", "pad")
	Settings.load_file()
	expect(is_equal_approx(Settings.volume("voice"), 0.4) and Settings.chars_per_second() == 30.0 and not Settings.auto_advance() and Settings.pad_hints(false), "settings did not come back from their file")
	Settings.apply()
	var i := AudioServer.get_bus_index("Voice")
	expect(i >= 0 and absf(AudioServer.get_bus_volume_db(i) - linear_to_db(0.4)) < 0.1, "the voice volume is not on the Voice bus")
	Settings.set_value("voice", "loud")
	Settings.set_value("text_speed", "ludicrous")
	expect(is_equal_approx(Settings.volume("voice"), 0.4) and Settings.get_value("text_speed") == "slow", "a setting took a value of the wrong kind")
	Settings.values = Settings.defaults()
	Settings.apply()


# ---------- save and load ----------

func _save_round_trip() -> void:
	var m = main_node()
	var at: Vector3 = m.nav.nav_point(Vector3(3.0, 0.0, 3.0))
	m.player.global_position = at
	m.inventory.add("tally_stick")
	m.quest.set_flag("check_flag", 7)
	m.quest.set_flag("bell_looked", true)
	m.skills.set_value("logic", 5)
	var key := Dialogue.check_key("save", "logic", 9, "red")
	var rolled: Dictionary = m.skills.roll(key, "logic", 9, "red")
	m.journal.update("open_task", "Look in the hay.")
	m.journal.update("closed_task", "Ask the cook.")
	m.journal.finish("closed_task")
	expect(m.session.save("slot_1", "Round trip"), "the save could not be written")
	expect(m.session.save(Saves.QUICK), "the quick save could not be written")
	var listed: Array = Saves.entries().filter(func(e): return e.slot == "slot_1")
	expect(listed.size() == 1 and listed[0].name == "Round trip" and listed[0].location == "courtyard" and listed[0].when.length() == 16 and "Ask the cook" in Saves.quest_line(listed[0]), "the save list does not say where, when and what the task was")
	expect(Saves.latest().slot == Saves.QUICK and Saves.entries().size() == 2, "the newest save is not the one written last")
	m.player.global_position = m.nav.nav_point(Vector3(-5.0, 0.0, 4.0))
	m.inventory.remove("tally_stick")
	m.quest.set_flag("check_flag", 0)
	m.quest.set_flag("bell_looked", false)
	m.skills.set_value("logic", 1)
	m.skills.rolls.clear()
	m.journal.entries.clear()
	expect(m.session.load_save("slot_1"), "the save could not be read back")
	var n = await _next_main(m)
	expect(n != null, "loading did not rebuild the world")
	if n == null:
		return
	expect(n.player.global_position.distance_to(at) < 0.2, "the position did not come back (%s, saved %s)" % [n.player.global_position, at])
	expect(n.inventory.has("tally_stick"), "the satchel did not come back")
	expect(n.quest.get_flag("check_flag") == 7, "the quest flag did not come back")
	expect(n.quest.flag("bell_looked"), "the story variable did not come back")
	expect(not n.rig.in_intro(), "a loaded world replays the intro")
	expect(n.skills.value("logic") == 5, "the skill values did not come back")
	var back: Dictionary = n.skills.roll(key, "logic", 9, "red")
	expect(not back.fresh and back.total == rolled.total and back.dice == rolled.dice, "a loaded game rolled a made check again")
	expect(n.journal.entries.get("open_task", {}).get("text") == "Look in the hay." and not n.journal.is_done("open_task") and n.journal.is_done("closed_task"), "the journal did not come back")


# ---------- locations ----------

func _locations() -> void:
	var m = main_node()
	expect(not m.session.travel("nowhere"), "travel to a location without an export did not fail")
	expect(not m.session.traveling, "a failed travel left the session travelling")
	# people stand where their data says, or at their fallback while the location has no export
	var fallback := {location = "courtyard", position = [1, 0, 1]}
	var unbuilt := {id = "t", name = "T", location = "unbuilt_home", position = [0, 0, 0], fallback = fallback}
	expect(m._placed(unbuilt).get("position") == [1, 0, 1], "a person with an unbuilt home did not take the fallback place")
	expect(m._placed({id = "t", location = "unbuilt_home"}).is_empty(), "a person of another location stands in the courtyard")
	# a location that has an export, with the courtyard's data standing in for it
	Locations.overrides["annex"] = "data/scene.json"
	expect(m._placed({id = "t", location = "annex", fallback = fallback}).is_empty(), "a person whose home is built still takes the fallback place")
	Locations.overrides["cookhouse"] = "data/scene.json"
	m.inventory.add("tally_stick")
	m.quest.set_flag("check_flag", 7)
	expect(m.session.travel("cookhouse", "cookhouse"), "travel to a location with an export failed")
	var n = await _next_main(m)
	expect(n != null and n.session.location == "cookhouse", "the new location was not built")
	if n == null:
		return
	expect(n.npc_by_id("marl") == null and n.npc_by_id("hedda") != null, "the cookhouse does not hold Hedda alone")
	expect(n.inventory.has("tally_stick") and n.quest.get_flag("check_flag") == 7, "the state did not travel")
	expect(n.session.visited.has("courtyard") and n.session.visited.has("cookhouse"), "visited places were not kept")
	expect(Saves.has(Saves.AUTO), "no autosave after a change of location")
	await _frames(60)
	# back out: the courtyard's cookhouse door leads here, so the figure stands at it
	expect(n.session.travel("courtyard", "door"), "travel back to the courtyard failed")
	var back = await _next_main(n)
	expect(back != null and back.session.location == "courtyard", "the courtyard was not rebuilt")
	if back == null:
		return
	var door: Vector3 = back.nav.exits.filter(func(e): return e.target == "cookhouse")[0].pos
	expect(back.player.global_position.distance_to(door) < 2.5, "the figure did not arrive at the cookhouse door (%s, door %s)" % [back.player.global_position, door])
	expect(back.npc_by_id("marl") != null, "Marl is not back in the courtyard")


# ---------- the end of a chapter ----------

## The text of every label of a page.
func _texts(n: Node) -> String:
	var out: String = n.text + "\n" if (n is Label or n is RichTextLabel) else ""
	for c in n.get_children():
		out += _texts(c)
	return out


## The title screen's button called `text`, or null.
func _title_button(n: Node, text: String) -> Button:
	for c in n.menu.column.get_children():
		if c is Button and c.text == text:
			return c
	return null


## end_chapter in a story: the lines before it are read, the screen goes dark and a card shows the
## chapter's title; the autosave holds the card; Continue leads to the page of choices, which
## names what the story variables and the rolls say; Back to the title ends it; the title's
## Continue is off and Load shows the card again.
func _chapter() -> void:
	var m = main_node()
	await _within(func(): return m.ui.fade.modulate.a < 0.001, 4.0)      # the courtyard's own fade-in is over
	ChapterUI.fade_s = 0.05
	ChapterUI.dwell_s = 0.1
	Dialogue.chapter_read_s = 0.2
	var def: Dictionary = m.chapter.chapters.def("night_one")
	expect(not def.is_empty() and def.get("title", "") != "", "data/chapters.json has no chapter night_one")
	# the page's rows follow the values of the story variables: a boolean by its word, a missing text leaves the row out
	var vars := {letter_outcome = "marl", tam_woken = true, knows_ford = false, player_claim = "silent"}
	var rows := Chapters.rows(def, func(n): return vars.get(n, ""))
	expect(rows.size() >= 3 and rows.any(func(r): return r.text.begins_with("You gave Marl")) and rows.any(func(r): return r.text.begins_with("You woke")), "the chapter's rows do not follow the variables: %s" % [rows])
	m.quest.set_flag("letter_outcome", "marl")
	m.quest.set_flag("tam_woken", true)
	m.quest.set_flag("player_claim", "silent")
	m.skills.roll(Dialogue.check_key("chapter", "composure", 12, "red"), "composure", 12, "red")

	var d := fixture_dialogue(m)
	m.ui.begin_conversation(null)
	d._begin("ending", "", "Test")
	expect(await _within(func(): return "last line before the card" in m.ui.log_text.text, 3.0), "the line before end_chapter did not show")
	expect(not m.chapter.active, "the chapter ended before the last line was read")
	expect(await _within(func(): return m.chapter.page == "card", 6.0), "end_chapter did not bring the card")
	expect(not "never shown" in m.ui.log_text.text, "a line after end_chapter was shown")
	expect(m.session.chapter_end == "night_one" and m.ui.busy and m.ui.fade.modulate.a > 0.99 and not m.ui.is_open(), "the screen is not dark and held at the card")
	expect(String(def.title).to_upper() in _texts(m.chapter.card_page).to_upper(), "the card does not show the chapter's title")
	var saved := Saves.read(Saves.AUTO)
	expect(saved.get("chapter_end") == "night_one" and Saves.latest().get("chapter") == "night_one", "the save made at the card does not say where it stands")
	m.chapter._on_continue()
	expect(await _within(func(): return m.chapter.page == "summary", 4.0), "Continue did not bring the page of choices")
	var text := _texts(m.chapter.summary_page)
	expect("You gave Marl the letter" in text and "held the captain's eye" in text, "the page of choices does not name what the story says")
	expect(m.skills.skill_name("composure").to_upper() in text and ("Passed" in text or "Failed" in text), "the page of choices does not list the checks made")
	d.queue_free()

	# the page leads back to the title, whose Continue is off for the save at the end of the chapter
	m.chapter._on_leave()
	var n = await _next_main(m)
	expect(n != null and n.menu.is_open() and n.menu.screen == "title", "the chapter did not lead back to the title")
	if n == null:
		return
	var cont := _title_button(n, "Continue")
	expect(cont != null and cont.disabled and "not yet written" in _texts(n.menu.column), "the title offers Continue after the end of a chapter")
	# Load shows the card again, with the variables of the save
	n.menu._load(Saves.AUTO)
	var c = await _next_main(n)
	expect(c != null and await _within(func(): return c.chapter.page == "card", 8.0), "the save made at the card did not load to the card")
	if c == null:
		return
	expect(c.session.chapter_end == "night_one" and c.quest.get_flag("letter_outcome") == "marl" and c.ui.busy, "the loaded card lost the story's state")
	c.chapter._on_continue()
	expect(await _within(func(): return c.chapter.page == "summary", 4.0) and "You gave Marl the letter" in _texts(c.chapter.summary_page), "the loaded page of choices is not the same")
	ChapterUI.fade_s = 1.4
	ChapterUI.dwell_s = 2.4
	Dialogue.chapter_read_s = 2.5


## "Quit to title" builds the world again with the title screen over it and the intro held.
func _title() -> void:
	var m = main_node()
	expect(m.session.to_title(), "to_title was refused")
	var n = await _next_main(m)
	expect(n != null and n.menu.is_open() and n.menu.mode == "title" and n.rig.held and n.ui.busy, "the title screen did not come up")
	if n == null:
		return
	expect(n.menu.screen == "title" and n.menu.column.get_child_count() > 4, "the title screen has no menu")
	n.menu._show("load")
	expect(n.menu.panel.visible and not n.menu.column.visible, "the load screen is not showing")
	# New game from the title: the build goes to the skills and the held intro plays from its wide view
	n.menu._show("new_game")
	n.menu._pick_build("level")
	var held_zoom: float = n.rig.zoom
	n.menu._begin_game()
	expect(not n.rig.held and n.rig.in_intro() and n.rig.zoom < 0.6 and absf(n.rig.zoom - held_zoom) < 0.01, "Begin did not let the held intro play from its wide view")
	expect(n.skills.archetype == "level" and n.skills.value("composure") == 3, "the title's build did not reach the skills")
	n.menu.close()
	expect(not n.menu.is_open() and not n.ui.busy, "closing the menu left the game blocked")


## The main node that replaces `old` after a load or a change of location.
func _next_main(old: Node) -> Node:
	var id := old.get_instance_id()
	await _until(func(): return not is_instance_id_valid(id) and main_node() != null and main_node().session.placed, 600)
	return main_node()
