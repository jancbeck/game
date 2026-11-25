## Plays the story for the player: a conversation with a person (knot talk_<id>) or the text of
## an object the player examines (knot look_<hotspot id>), in the dialogue column of ui.gd.
##
## The story is run ahead to its next choice (or its end), and what it said is played back as a
## timeline: each line is logged when the one before has been spoken, a voiced line plays its clip
## through the speaker's figure (npc.gd, which also drives the talking portrait), and the responses
## appear after the last line. Confirm skips the line being spoken.
##
## Tags: `# speaker:<npc id>` says who speaks (default: the person talked to; narration at an
## object; `narrator` forces narration), `# line:<clip id>` voices the line with
## assets/npcs/<speaker>/<clip id>.wav.
##
## A skill speaks with `# skill:<id>`; with `# passive:<number or difficulty name>` as well the line
## is heard only when the skill + 6 reaches the number. `# line:<clip>` on such a line plays
## assets/skills/<clip>.wav, one folder for every skill, on the Voice bus; the ambience ducks while
## it plays. `# journal:<task>:<text>` writes the journal, `# journal_done:<task>` closes a task.
##
## Lines follow each other on their own (settings.gd: auto-advance), each after the last has been
## spoken and its text has appeared (the text speed); with auto-advance off every line waits for
## the player's confirm or click (`advance()`).
##
## A choice can carry a check, written inside its brackets: `+ [Press him #check:authority:12:white]`
## (skill, difficulty as number or name, "white" or "red", optionally the flag whose being set lets a
## failed white check be tried again). The option shows the skill, the difficulty and the chance, and
## the body of the choice makes the roll with roll("authority", 12, "white"), which answers true or
## false. A result is kept: a red check is made once, a white one again only after the skill has risen
## (or the named flag is set), until then the option is locked.
##
## The story calls the game through the EXTERNALs bound in setup(): give_item, take_item, has_item,
## set_flag, get_flag, play_line, roll, skill_value, skill_add, end_chapter. `end_chapter("<id>")` ends
## the chapter (data/chapters.json) once the lines before it have been read: the column closes and
## chapter_ui.gd takes over.
extends Node

const SceneData := preload("res://scripts/scene_data.gd")
const Settings := preload("res://scripts/settings.gd")

const BEAT_S := 0.25         # pause after a line without a voice

## Where `# line:<clip>` on a skill finds its clip; checks point it at a scratch folder.
static var skill_dir := "res://assets/skills"
## The last line before an end_chapter stands this long, in seconds, after it has been read.
static var chapter_read_s := 2.5

var main
var story
var active := false
var _speaker := ""           # the person talked to; "" at an object
var _narrator := ""          # name above narration: the object's, or none in a conversation
var _timeline: Array = []
var _choices: Array = []     # story.choice_list() of the options on offer
var _checks: Array = []      # per choice: its check {key, skill, dc, kind, retry}, or {}
var _pending := {}           # the check of the choice just taken, for the roll the story makes next
var _hold := 0.0
var _voice = null            # npc.gd whose clip is playing
var _skill_voice: AudioStreamPlayer
var _skill_until := 0        # when the skill's clip ends (ms); the Dummy audio driver never reports it
var _gated := false          # auto-advance is off: the line is read, the next waits for the player


func setup(m, s) -> void:
	main = m
	story = s
	main.ui.closed.connect(_on_closed)
	main.ui.advance_requested.connect(advance)
	_skill_voice = AudioStreamPlayer.new()
	_skill_voice.bus = "Voice"
	add_child(_skill_voice)
	if story.ok():
		story.bind("give_item", self, "ext_give_item")
		story.bind("take_item", self, "ext_take_item")
		story.bind("has_item", self, "ext_has_item", true)
		story.bind("set_flag", self, "ext_set_flag")
		story.bind("get_flag", self, "ext_get_flag", true)
		story.bind("play_line", self, "ext_play_line")
		story.bind("roll", self, "ext_roll")
		story.bind("skill_value", self, "ext_skill_value", true)
		story.bind("skill_add", self, "ext_skill_add")
		story.bind("end_chapter", self, "ext_end_chapter")


func has_look(hotspot_id: String) -> bool:
	return story.has_knot("look_" + hotspot_id)


func has_talk(npc) -> bool:
	return story.has_knot(_talk_knot(npc))


func _talk_knot(npc) -> String:
	return npc.def.get("knot", "talk_" + npc.def.id)


func begin_look(hotspot: Dictionary) -> void:
	main.ui.begin_conversation(null)          # an object's text starts a log of its own
	_begin("look_" + hotspot.id, "", hotspot.name)


func begin_talk(npc) -> void:
	_begin(_talk_knot(npc), npc.def.id, "")


func _begin(knot: String, speaker: String, narrator: String) -> void:
	active = true
	_speaker = speaker
	_narrator = narrator
	_timeline.clear()
	_hold = 0.0
	_gated = false
	main.ui.set_options_visible(false)
	story.goto(knot)
	_pump()


## Runs the story to its next choice or its end, queueing everything it says. What changes the
## game (the journal, a roll) happens now; the timeline only shows it.
func _pump() -> void:
	while story.can_continue():
		var line: Dictionary = story.next_line()
		var entry := _entry_of(line)
		if not entry.is_empty():
			_timeline.append(entry)
		for note in _journal_tags(line):
			_timeline.append({kind = "toast", text = note})
	_choices = story.choice_list()
	_timeline.append({kind = "options"})


## The timeline entry of a line of the story: {} when nothing is shown (an empty line, or a passive
## check the skill does not reach).
func _entry_of(line: Dictionary) -> Dictionary:
	var tags: Dictionary = line.tags
	var skills = main.skills
	if tags.has("skill") and skills.has_skill(tags.skill) and line.text != "":
		var bracket := ""
		if tags.has("passive"):
			var dc: int = skills.parse_dc(tags.passive)
			if dc <= 0:
				push_error("dialogue: passive:%s is not a number or a difficulty" % tags.passive)
			elif not skills.passes(tags.skill, dc):
				return {}
			else:
				bracket = "%s: Success" % skills.difficulty_name(dc)
		return {kind = "skill", skill = tags.skill, bracket = bracket, text = line.text, tags = tags}
	if tags.has("skill") and not skills.has_skill(tags.skill):
		push_error("dialogue: no skill '%s' in data/skills.json" % tags.skill)
	if line.text == "":
		return {}
	return {kind = "line", text = line.text, tags = tags}


## Applies the journal tags of a line; returns the notices to show.
func _journal_tags(line: Dictionary) -> Array:
	var notes := []
	var journal = main.journal
	for kv in line.all:
		if kv[0] == "journal":
			var i: int = kv[1].find(":")
			if i <= 0:
				push_error("dialogue: journal tag '%s' is not <task>:<text>" % kv[1])
				continue
			var id: String = kv[1].substr(0, i).strip_edges()
			var fresh: bool = not journal.has(id)
			if journal.update(id, kv[1].substr(i + 1).strip_edges()):
				notes.append("%s: %s" % ["New task" if fresh else "Journal updated", journal.title(id)])
		elif kv[0] == "journal_done":
			if journal.finish(kv[1]):
				notes.append("Task done: %s" % journal.title(kv[1]))
	return notes


func _process(delta: float) -> void:
	if not active or _timeline.is_empty():
		return
	var kind: String = _timeline[0].kind
	if kind != "options":
		if main.ui.revealing():
			return
		if _hold > 0.0:
			_hold -= delta
			return
		if _voice != null and _voice.is_speaking():
			return
		if _gated and kind in ["line", "skill", "roll"]:
			return
	_play(_timeline.pop_front())
	if kind in ["line", "skill", "roll"]:
		_gated = not Settings.auto_advance()


func _play(e: Dictionary) -> void:
	match e.kind:
		"line":
			var who: String = e.tags.get("speaker", _speaker)
			var narration: bool = who == "" or who == "narrator"
			main.ui.say(_narrator if narration else main.npc_name(who), e.text)
			_voice = null
			if not narration and e.tags.has("line"):
				_start_voice(who, e.tags.line)
			if _voice == null:
				_hold = BEAT_S
		"skill":
			var id: String = e.skill
			main.ui.say_skill(main.skills.skill_name(id), main.skills.color_of(id), e.bracket, main.ui.WHITE_CHECK, e.text)
			_voice = null
			_hold = BEAT_S
			if e.tags.has("line"):
				_hold = maxf(_hold, _start_skill_voice(e.tags.line))
		"roll":
			_log_roll(e.roll)
			_voice = null
			_hold = BEAT_S
		"voice":
			_start_voice(e.speaker, e.clip)
		"toast":
			main.inventory_ui.toast(e.text)
		"hold":
			_hold = e.seconds
		"chapter":
			_timeline.clear()
			main.chapter.begin(e.id)
		"options":
			main.ui.set_options(_option_views(), _choose)
			main.ui.set_options_visible(true)


func _start_voice(who: String, clip: String) -> void:
	var npc = main.npc_by_id(who)
	_voice = npc if npc != null and npc.speak(clip) else null


## True while lines are still to come, before the responses; confirm skips to the next one.
func waiting() -> bool:
	return active and _timeline.any(func(e): return e.kind != "options")


## True while a person's clip or a skill's clip is playing (the ambience ducks under it).
func voice_active() -> bool:
	return (_voice != null and _voice.is_speaking()) or Time.get_ticks_msec() < _skill_until


## The player's confirm or click on the column: with auto-advance off the first press shows the
## rest of a line that is still appearing and the next goes on; otherwise it goes on at once.
func advance() -> void:
	if not waiting():
		return
	if not Settings.auto_advance() and main.ui.revealing():
		main.ui.finish_reveal()
		return
	skip()


## Cuts off the voice and the text still appearing and lets the next line come.
func skip() -> void:
	if _voice != null:
		_voice.stop_speaking()
	_skill_voice.stop()
	_skill_until = 0
	_hold = 0.0
	_gated = false
	main.ui.finish_reveal()


func _choose(i: int) -> void:
	if main.ui.is_locked(i):
		return
	skip()    # an answer cuts off the line still being spoken
	var label: String = _choices[i].text
	if not label.begins_with("["):    # spoken choices go into the log; [Leave.] and the like do not
		main.ui.say("You", label)
	main.ui.set_options_visible(false)
	_pending = _checks[i] if i < _checks.size() else {}
	story.choose(i)
	_pump()
	_pending = {}


# ---------- checks ----------

## The key a check's result is kept under: the knot, the skill, the difficulty and the colour.
static func check_key(knot: String, skill: String, dc: int, kind: String) -> String:
	return "%s|%s|%d|%s" % [knot, skill, dc, kind]


## The check a choice carries, from `#check:<skill>:<difficulty>[:<white|red>[:<retry flag>]]`; {} for none.
func _check_of(c: Dictionary) -> Dictionary:
	if not c.tags.has("check"):
		return {}
	var f: PackedStringArray = String(c.tags.check).split(":")
	var skill := f[0].strip_edges().to_lower()
	var dc: int = main.skills.parse_dc(f[1]) if f.size() > 1 else 0
	var kind := f[2].strip_edges().to_lower() if f.size() > 2 else "white"
	if not main.skills.has_skill(skill) or dc <= 0 or not kind in ["white", "red"]:
		push_error("dialogue: the check tag '%s' on '%s' is not <skill>:<difficulty>[:white|red[:flag]]" % [c.tags.check, c.text])
		return {}
	return {key = check_key(c.knot, skill, dc, kind), skill = skill, dc = dc, kind = kind,
		retry = f[3].strip_edges() if f.size() > 3 else ""}


func _flag_now(chk: Dictionary) -> bool:
	return chk.get("retry", "") != "" and main.quest.flag(chk.retry)


## What the column shows for each option: the text, or for a check the text with its tag and lock.
func _option_views() -> Array:
	_checks = _choices.map(_check_of)
	var views := []
	for i in _choices.size():
		var c: Dictionary = _choices[i]
		var chk: Dictionary = _checks[i]
		if chk.is_empty():
			views.append(c.text)
			continue
		var sk = main.skills
		var st: Dictionary = sk.state_of(chk.key, chk.skill, chk.dc, _flag_now(chk))
		var red: bool = chk.kind == "red"
		var parts: Array[String] = [sk.skill_name(chk.skill), "%s %d" % [sk.difficulty_name(chk.dc), chk.dc]]
		if st.locked:
			parts.append("failed, no second chance" if red else "failed, retry when %s rises%s" % [sk.skill_name(chk.skill), " or something changes" if chk.retry != "" else ""])
		elif st.passed:
			parts.append("passed")
		else:
			parts.append("%d%%" % roundi(st.chance * 100.0))
			if st.failed:
				parts.append("retry")
			elif red:
				parts.append("one try")
		views.append({text = c.text, tag = " · ".join(parts), locked = st.locked,
			tag_color = main.ui.RED_CHECK if red else main.ui.WHITE_CHECK})
	return views


func _log_roll(rec: Dictionary) -> void:
	var sk = main.skills
	var d: Array = rec.dice
	var detail := "Rolled %d + %d, plus %d = %d against %d." % [d[0], d[1], rec.value, rec.total, rec.dc]
	if d[0] == 6 and d[1] == 6:
		detail = "Rolled 6 + 6, boxcars: it cannot fail."
	elif d[0] == 1 and d[1] == 1:
		detail = "Rolled 1 + 1, snake eyes: it cannot succeed."
	main.ui.say_skill(sk.skill_name(rec.skill), sk.color_of(rec.skill),
		"%s %d: %s" % [sk.difficulty_name(rec.dc), rec.dc, "Success" if rec.success else "Failure"],
		main.ui.RED_CHECK if rec.kind == "red" else main.ui.WHITE_CHECK, detail)


## Plays assets/skills/<clip>.wav; returns its length (0 when there is no such clip).
func _start_skill_voice(clip: String) -> float:
	var path := "%s/%s.wav" % [skill_dir, clip]
	if not FileAccess.file_exists(path):
		return 0.0
	var stream := AudioStreamWAV.load_from_file(path)
	if stream == null:
		return 0.0
	_skill_voice.stream = stream
	_skill_voice.play()
	_skill_until = Time.get_ticks_msec() + int(stream.get_length() * 1000.0)
	return stream.get_length()


func _on_closed() -> void:
	active = false
	_timeline.clear()
	_voice = null
	_hold = 0.0
	_pending = {}
	_gated = false
	_skill_voice.stop()
	_skill_until = 0


# ---------- what the story can call ----------

func _note(text: String) -> void:
	if active:
		_timeline.append({kind = "toast", text = text})
	else:
		main.inventory_ui.toast(text)


func ext_give_item(id: String) -> void:
	if main.inventory.add(id):
		_note("Taken: %s" % main.inventory.item_name(id))


func ext_take_item(id: String) -> void:
	var name: String = main.inventory.item_name(id)
	if main.inventory.remove(id):
		_note("Gone from your satchel: %s" % name)


func ext_has_item(id: String) -> bool:
	return main.inventory.has(id)


func ext_set_flag(name: String, value) -> void:
	main.quest.set_flag(name, value)


func ext_get_flag(name: String):
	return main.quest.get_flag(name)


func ext_play_line(who: String, clip: String) -> void:
	if active:
		_timeline.append({kind = "voice", speaker = who, clip = clip})
	else:
		_start_voice(who, clip)


## The check the story makes: true on success. The result is kept under the key of the choice that
## led here (or of the knot, for a roll made in the text), so it is made once per check.
func ext_roll(skill, difficulty, kind) -> bool:
	var id := str(skill).to_lower()
	var dc: int = main.skills.parse_dc(difficulty)
	var k := "red" if str(kind).to_lower() == "red" else "white"
	if not main.skills.has_skill(id) or dc <= 0:
		push_error("roll(%s, %s, %s): not a skill of data/skills.json and a difficulty" % [skill, difficulty, kind])
		return false
	var chk: Dictionary = _pending if _pending.get("skill") == id and _pending.get("dc") == dc and _pending.get("kind") == k else {}
	var key: String = chk.key if not chk.is_empty() else check_key(story.current_knot(), id, dc, k)
	var rec: Dictionary = main.skills.roll(key, id, dc, k, _flag_now(chk))
	if rec.fresh and active:
		_timeline.append({kind = "roll", roll = rec})
	return rec.success


## Ends the chapter `id` after the lines said so far have been read; what follows in the story is not shown.
func ext_end_chapter(id) -> void:
	if active:
		_timeline.append({kind = "hold", seconds = chapter_read_s})
		_timeline.append({kind = "chapter", id = str(id)})
	else:
		main.chapter.begin(str(id))


func ext_skill_value(skill) -> int:
	return main.skills.value(str(skill).to_lower())


## Raises (or lowers) a skill, with a notice.
func ext_skill_add(skill, amount) -> void:
	var id := str(skill).to_lower()
	if not main.skills.has_skill(id):
		push_error("skill_add: no skill '%s'" % skill)
		return
	main.skills.add(id, int(amount))
	_note("%s %s to %d" % [main.skills.skill_name(id), "rises" if int(amount) > 0 else "falls", main.skills.value(id)])
