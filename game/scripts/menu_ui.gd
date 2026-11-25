## The title screen, the pause menu and the screens they open: new game with its builds, the load
## and save lists, the settings. One panel style with the dialogue column (dark, brass rule,
## serif); the world keeps running behind it.
##
## Title: the courtyard's wide view drifting behind the name, rain on the ambience bus. Continue
## loads the newest save, New game asks for a build (data/archetypes.json, or Custom: spend the
## points on the six skills) and then lets the held intro play, Load lists the saves (where, when,
## the task written last), Settings is settings.gd. Esc or the pad's B opens the pause menu in play
## (Resume, Save, Load, Settings, Quit to title, Quit game).
##
## Mouse, keys and pad share Godot's focus: Up and Down (D-pad, left stick) move, Enter or A
## presses, Left and Right (D-pad) adjust a slider or step a setting, Esc or B goes back. The menu
## sits one layer under the fade, so a fade to black covers it. While it is open `main.ui.busy` is
## set, which stops hover, clicks, the pad and the exits.
##
## The title shows only on a fresh start without a debugging or check flag, and after "Quit to
## title" (`wanted()`).
extends CanvasLayer

const Settings := preload("res://scripts/settings.gd")
const Saves := preload("res://scripts/saves.gd")
const Locations := preload("res://scripts/locations.gd")

const NAME := "Varrow Gate"
const INK := Color(0.86, 0.83, 0.76)
const GOLD := Color("#d9b77a")
const GOLD_HOT := Color("#f2dcae")
const DIM := Color(0.62, 0.59, 0.54)
const BRASS := Color(0.55, 0.45, 0.3)
const PANEL_BG := Color(0.035, 0.035, 0.04)
const EDGE_X := 190                 # the left column's distance from the screen edge
const TEXT_SPEEDS := ["instant", "fast", "normal", "slow"]
const HINTS := ["auto", "mouse", "pad"]

## Flags that start straight in the world: debugging and the checks.
const SKIP_FLAGS := ["--no-intro", "--start=", "--data=", "--capture", "--snap", "--clip=", "--npc-check",
	"--perf-check", "--ui-check", "--char-check", "--release-shot="]

static var enabled := true          # smoke.gd turns it off: the checks play the world, not the title

var main
var font: SystemFont
var title_font: FontVariation
var root: Control
var shade: ColorRect
var veil: TextureRect
var column: VBoxContainer           # the left column: title and pause menu
var panel: PanelContainer           # the centred panel: every other screen
var hint: Label
var status: Label
var mode := ""                      # "title" or "pause"; "" while closed
var screen := ""
var chosen := ""                    # the build picked on the new game screen ("custom" for the points)
var build := {}                     # the custom build being spent
var save_slot := ""                 # the slot the save screen is naming
var _back_stack: Array[String] = []
var _starting := false
var _status_tween: Tween
var _hint_pad := false
var _first: Control
var _theme: Theme
var _begin: Button
var _points: Label
var _detail: VBoxContainer
var _build_rows := {}               # build id -> Button
var _sliders := {}                  # skill id -> HSlider (custom build)


## Whether this start of the game begins at the title screen.
static func wanted(pending: Dictionary) -> bool:
	if pending.get("title", false):
		return true
	if not enabled or not pending.is_empty():
		return false
	for a in OS.get_cmdline_user_args():
		for flag in SKIP_FLAGS:
			if a.begins_with(flag):
				return false
	return true


func setup(m) -> void:
	main = m
	layer = 9
	font = main.ui.font
	title_font = FontVariation.new()
	var serif := SystemFont.new()
	serif.font_names = PackedStringArray(["Baskerville", "Hoefler Text", "Didot", "Georgia", "serif"])
	serif.antialiasing = TextServer.FONT_ANTIALIASING_GRAY
	title_font.base_font = serif
	title_font.spacing_glyph = 20
	_theme = _make_theme()

	root = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_STOP
	root.theme = _theme
	root.visible = false
	add_child(root)

	shade = ColorRect.new()
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(shade)
	veil = _veil()
	root.add_child(veil)

	var left := MarginContainer.new()
	left.set_anchors_preset(Control.PRESET_FULL_RECT)
	left.add_theme_constant_override("margin_left", EDGE_X)
	left.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(left)
	column = VBoxContainer.new()
	column.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	column.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	column.add_theme_constant_override("separation", 6)
	left.add_child(column)

	var middle := CenterContainer.new()
	middle.set_anchors_preset(Control.PRESET_FULL_RECT)
	middle.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(middle)
	panel = PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(PANEL_BG, 0.95)
	sb.border_color = Color(BRASS, 0.5)
	sb.set_border_width_all(1)
	sb.border_width_top = 2
	sb.content_margin_left = 44
	sb.content_margin_right = 44
	sb.content_margin_top = 32
	sb.content_margin_bottom = 30
	panel.add_theme_stylebox_override("panel", sb)
	middle.add_child(panel)

	hint = _label("", 22, DIM)
	_pin_bottom(hint, -72)
	hint.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	hint.add_theme_constant_override("outline_size", 6)
	root.add_child(hint)
	status = _label("", 28, GOLD)
	_pin_bottom(status, -128)
	status.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	status.add_theme_constant_override("outline_size", 8)
	status.modulate.a = 0.0
	root.add_child(status)


## A label at the left edge, `top` pixels above the bottom of the screen.
func _pin_bottom(l: Label, top: int) -> void:
	l.anchor_top = 1.0
	l.anchor_bottom = 1.0
	l.offset_left = EDGE_X
	l.offset_top = top
	l.offset_right = 1600
	l.offset_bottom = top + 40


func _veil() -> TextureRect:
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.5, 1.0])
	g.colors = PackedColorArray([Color(0.01, 0.012, 0.018, 0.92), Color(0.01, 0.012, 0.018, 0.6), Color(0.01, 0.012, 0.018, 0.0)])
	var t := GradientTexture2D.new()
	t.gradient = g
	t.fill_from = Vector2(0, 0)
	t.fill_to = Vector2(1, 0)
	t.width = 256
	t.height = 4
	var r := TextureRect.new()
	r.texture = t
	r.stretch_mode = TextureRect.STRETCH_SCALE
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.anchor_bottom = 1.0
	r.offset_right = 1500
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r


# ---------- opening and closing ----------

func is_open() -> bool:
	return root != null and root.visible


func open_title() -> void:
	_open("title")
	root.modulate.a = 0.0
	create_tween().tween_property(root, "modulate:a", 1.0, 1.8)


## The pause menu. Refused while something else holds the screen.
func open_pause() -> bool:
	if is_open() or main.ui.busy or main.ui.is_open() or main.session.traveling:
		return false
	main.player.stop()
	main.sheet_ui.close()
	main.inventory_ui.close()
	_open("pause")
	return true


func _open(which: String) -> void:
	mode = which
	_back_stack.clear()
	screen = ""
	_starting = false
	main.ui.busy = true
	root.modulate.a = 1.0
	root.visible = true
	_show(which)


func close() -> void:
	if not is_open():
		return
	root.visible = false
	mode = ""
	main.ui.busy = main.session.traveling


func _input(event: InputEvent) -> void:
	if is_open() and event.is_action_pressed("ui_cancel") and not event.is_echo():
		get_viewport().set_input_as_handled()
		_back()


func _back() -> void:
	if _starting:
		return
	if not _back_stack.is_empty():
		_show(_back_stack.pop_back(), false)
	elif mode == "pause":
		close()


func _process(_delta: float) -> void:
	if is_open():
		var pad: bool = Settings.pad_hints(main.pad != null and main.pad.active)
		if pad != _hint_pad:
			_refresh_hint()


# ---------- screens ----------

func _show(id: String, remember := true) -> void:
	if remember and screen != "" and screen != id:
		_back_stack.append(screen)
	screen = id
	for holder in [column, panel]:
		for c in holder.get_children():
			holder.remove_child(c)
			c.queue_free()
		holder.visible = false
	_first = null
	_build_rows.clear()
	_sliders.clear()
	var root_screen := id == mode
	veil.visible = id == "title"
	shade.color = Color(0, 0, 0, 0.1 if id == "title" else 0.62)
	column.visible = root_screen
	panel.visible = not root_screen
	call("_screen_" + id)
	_refresh_hint()
	_focus_first.call_deferred()


## The theme of the menus (dark, brass, serif), for the other screens that draw buttons.
func ui_theme() -> Theme:
	return _theme


func _focus_first() -> void:
	if _first != null and is_instance_valid(_first) and _first.is_inside_tree():
		_first.grab_focus()


func _screen_title() -> void:
	var name_label := _label(NAME.to_upper(), 124, GOLD)
	name_label.add_theme_font_override("font", title_font)
	name_label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.7))
	name_label.add_theme_constant_override("shadow_offset_x", 0)
	name_label.add_theme_constant_override("shadow_offset_y", 5)
	column.add_child(name_label)
	column.add_child(_rule(660))
	column.add_child(_gap(54))
	var latest := Saves.latest()
	if not latest.is_empty():
		var ended: bool = str(latest.get("chapter", "")) != ""
		var go := _item("Continue", func(): _load(latest.slot))
		if ended:
			# the newest save stands at the end of a chapter and nothing follows it yet: Load shows its card
			go.disabled = true
			_first = null
			column.add_child(_note("Continue the story (not yet written)"))
		else:
			column.add_child(_note("%s  ·  %s" % [Locations.title(main.data.config, latest.location), latest.when]))
		column.add_child(_gap(14))
	_item("New game", func(): _show("new_game"))
	_item("Load", func(): _show("load"))
	_item("Settings", func(): _show("settings"))
	_item("Quit", func(): get_tree().quit())


func _screen_pause() -> void:
	column.add_child(_label("PAUSED", 28, GOLD))
	column.add_child(_rule(520))
	column.add_child(_gap(24))
	_item("Resume", close)
	_item("Save", func(): _show("save"))
	_item("Load", func(): _show("load"))
	_item("Settings", func(): _show("settings"))
	column.add_child(_gap(18))
	_item("Quit to title", func(): _show("confirm_title"))
	_item("Quit game", func(): _show("confirm_quit"))


func _screen_confirm_title() -> void:
	_confirm("Leave for the title screen? Progress since the last save is lost.", "Quit to title", func():
		_starting = main.session.to_title())


func _screen_confirm_quit() -> void:
	_confirm("Quit the game? Progress since the last save is lost.", "Quit game", func(): get_tree().quit())


func _confirm(text: String, yes: String, on_yes: Callable) -> void:
	var box := _panel_box(900)
	box.add_child(_wrap(text, 30, INK, 900))
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 30)
	box.add_child(row)
	var no := _button("Back", _back, row)
	_button(yes, on_yes, row)
	_first = no


# ---------- new game ----------

func _screen_new_game() -> void:
	var arch = main.session.archetypes
	var box := _panel_box(1780)
	box.add_child(_heading("NEW GAME"))
	var cols := HBoxContainer.new()
	cols.add_theme_constant_override("separation", 64)
	box.add_child(cols)

	var left := VBoxContainer.new()
	left.custom_minimum_size = Vector2(600, 0)
	left.add_theme_constant_override("separation", 6)
	cols.add_child(left)
	var rows: Array = arch.defs.map(func(d): return [d.id, d.name, _top_skills(d.skills)])
	rows.append(["custom", arch.custom.get("name", "Custom"), "Spend %d points yourself" % arch.points])
	for r in rows:
		var b := _build_row(r[0], r[1], r[2])
		left.add_child(b)
		_build_rows[r[0]] = b
	_first = _build_rows[chosen if _build_rows.has(chosen) else rows[0][0]]

	_detail = VBoxContainer.new()
	_detail.custom_minimum_size = Vector2(1000, 0)
	_detail.add_theme_constant_override("separation", 14)
	cols.add_child(_detail)

	var foot := HBoxContainer.new()
	foot.add_theme_constant_override("separation", 30)
	box.add_child(foot)
	_button("Back", _back, foot)
	_begin = _button("Begin", _begin_game, foot)
	_pick_build(chosen if _build_rows.has(chosen) else rows[0][0])


## The two skills a build is strongest in, for the line under its name.
func _top_skills(skills: Dictionary) -> String:
	var sk = main.skills
	var ids: Array = skills.keys()
	ids.sort_custom(func(a, b): return skills[a] > skills[b])
	return " · ".join(ids.slice(0, 2).map(func(id): return sk.skill_name(id)))


func _build_row(id: String, title: String, sub: String) -> Button:
	var b := Button.new()
	b.custom_minimum_size = Vector2(0, 92)
	b.focus_mode = Control.FOCUS_ALL
	var hover := StyleBoxFlat.new()
	hover.bg_color = Color(BRASS, 0.07)
	hover.set_content_margin_all(0)
	b.add_theme_stylebox_override("hover", hover)
	var v := VBoxContainer.new()
	v.set_anchors_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 24
	v.offset_top = 10
	v.offset_right = -20
	v.add_theme_constant_override("separation", 0)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	v.add_child(_label(title, 38, INK, true))
	v.add_child(_label(sub, 22, DIM, true))
	b.add_child(v)
	b.focus_entered.connect(func(): _pick_build(id))
	b.pressed.connect(func():
		_pick_build(id)
		if not _begin.disabled:
			_begin.grab_focus()
		else:
			_focus_first_slider())
	return b


## Makes `id` the build on show: its description and skills on the right.
func _pick_build(id: String) -> void:
	var arch = main.session.archetypes
	chosen = id
	for k in _build_rows:
		var style: StyleBox = null
		if k == id:
			var s := StyleBoxFlat.new()
			s.bg_color = Color(BRASS, 0.13)
			s.border_width_left = 4
			s.border_color = Color(GOLD, 0.55)
			style = s
		if style:
			_build_rows[k].add_theme_stylebox_override("normal", style)
		else:
			_build_rows[k].remove_theme_stylebox_override("normal")
	for c in _detail.get_children():
		_detail.remove_child(c)
		c.queue_free()
	_sliders.clear()
	var custom := id == "custom"
	var text: String = arch.custom.get("description", "") if custom else arch.find(id).description
	_detail.add_child(_wrap(text, 30, INK, 1000))
	_detail.add_child(_rule(1000))
	if custom and build.is_empty():
		build = arch.blank()
	var values: Dictionary = build if custom else arch.find(id).skills
	for d in main.skills.defs:
		_detail.add_child(_skill_row(d, int(values.get(d.id, 1)), custom))
	_points = _label("", 28, GOLD)
	_points.visible = custom
	_detail.add_child(_points)
	_update_points()


func _skill_row(d: Dictionary, value: int, editable: bool) -> Control:
	var color := Color(d.color)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 26)
	var names := VBoxContainer.new()
	names.custom_minimum_size = Vector2(580, 0)
	names.add_theme_constant_override("separation", 0)
	names.add_child(_label(String(d.name).to_upper(), 28, color))
	names.add_child(_label(d.get("description", ""), 20, DIM, true))
	row.add_child(names)
	var num := _label(str(value), 44, color)
	num.custom_minimum_size = Vector2(54, 0)
	num.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	if editable:
		var s := HSlider.new()
		s.min_value = 1
		s.max_value = 5
		s.step = 1
		s.value = value
		s.tick_count = 5
		s.custom_minimum_size = Vector2(300, 48)
		s.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		s.add_theme_color_override("font_color", color)
		s.value_changed.connect(func(v): _on_slider(d.id, v, s, num))
		s.focus_entered.connect(func(): num.add_theme_color_override("font_color", GOLD_HOT))
		s.focus_exited.connect(func(): num.add_theme_color_override("font_color", color))
		_sliders[d.id] = s
		row.add_child(s)
	else:
		row.add_child(_pips(value, color))
	row.add_child(num)
	return row


func _pips(value: int, color: Color) -> Control:
	var box := HBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	box.custom_minimum_size = Vector2(300, 0)
	box.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	for i in 5:
		var c := ColorRect.new()
		c.custom_minimum_size = Vector2(52, 14)
		c.color = color if i < value else Color(0.13, 0.125, 0.12)
		box.add_child(c)
	return box


## A slider of the custom build moved: the points in hand cannot be overspent.
func _on_slider(id: String, v: float, slider: HSlider, num: Label) -> void:
	var arch = main.session.archetypes
	var others: int = arch.spent(build) - (int(build[id]) - arch.low)
	var allowed: int = arch.low + arch.points - others
	var nv := mini(int(v), allowed)
	if nv != int(v):
		slider.set_value_no_signal(nv)
	build[id] = nv
	num.text = str(nv)
	_update_points()


func _update_points() -> void:
	var arch = main.session.archetypes
	var custom := chosen == "custom"
	var left: int = arch.left(build) if custom else 0
	if _points != null:
		_points.text = "Points left: %d" % left
	if _begin != null:
		_begin.disabled = custom and left != 0


func _focus_first_slider() -> void:
	if not _sliders.is_empty():
		_sliders[main.skills.defs[0].id].grab_focus()


func _begin_game() -> void:
	var arch = main.session.archetypes
	var b: Dictionary = build if chosen == "custom" else arch.find(chosen).skills
	if _starting or not arch.valid(b):
		return
	_starting = true
	main.begin_game(chosen, b.duplicate())
	var tw := create_tween()
	tw.tween_property(root, "modulate:a", 0.0, 1.2)
	await tw.finished
	close()


# ---------- load and save ----------

func _screen_load() -> void:
	var box := _panel_box(1480)
	box.add_child(_heading("LOAD"))
	var list := Saves.entries()
	if list.is_empty():
		box.add_child(_label("No saves yet.", 30, DIM))
	else:
		var rows := VBoxContainer.new()
		rows.add_theme_constant_override("separation", 8)
		for e in list:
			var slot: String = e.slot
			var b := _save_row(e)
			b.pressed.connect(func(): _load(slot))
			rows.add_child(b)
			if _first == null:
				_first = b
		box.add_child(_scrolled(rows, list.size()))
	var back := _button("Back", _back, box)
	if _first == null:
		_first = back


func _screen_save() -> void:
	var box := _panel_box(1480)
	box.add_child(_heading("SAVE"))
	var rows := VBoxContainer.new()
	rows.add_theme_constant_override("separation", 8)
	for slot in Saves.named_slots():
		var d := Saves.read(slot)
		var e: Dictionary = d.get("meta", {}).duplicate()
		e.slot = slot
		e.location = str(d.get("location", ""))
		var b := _save_row(e, d.is_empty())
		b.pressed.connect(func():
			save_slot = slot
			_show("save_name"))
		rows.add_child(b)
		if _first == null:
			_first = b
	box.add_child(_scrolled(rows, Saves.SLOT_COUNT))
	_button("Back", _back, box)


func _screen_save_name() -> void:
	var box := _panel_box(1100)
	box.add_child(_heading("SAVE"))
	var old: Dictionary = Saves.read(save_slot).get("meta", {})
	box.add_child(_label("Overwrite “%s”?" % Saves.label_of(old) if not old.is_empty() else "Name this save", 30, INK))
	var line := LineEdit.new()
	line.custom_minimum_size = Vector2(0, 64)
	line.max_length = 48
	line.text = _default_name()
	line.select_all_on_focus = true
	line.text_submitted.connect(func(t): _save_as(t))
	box.add_child(line)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 30)
	box.add_child(row)
	_button("Back", _back, row)
	_button("Save", func(): _save_as(line.text), row)
	_first = line


## The quest written last, else the place.
func _default_name() -> String:
	var q: Dictionary = main.journal.latest()
	return q.title if not q.is_empty() else Locations.title(main.data.config, main.session.location)


func _save_as(save_name: String) -> void:
	var n := save_name.strip_edges()
	if main.session.save(save_slot, n if n != "" else _default_name()):
		_back_stack.clear()
		_show("pause", false)
		say("Saved")
	else:
		say("Could not save")


func _load(slot: String) -> void:
	if _starting:
		return
	if main.session.load_save(slot):
		_starting = true
	else:
		say("Could not load that save")


## One save in a list: its name and where and when on the first line, the task written last below.
func _save_row(e: Dictionary, empty := false) -> Button:
	var b := Button.new()
	b.custom_minimum_size = Vector2(0, 100)
	b.focus_mode = Control.FOCUS_ALL
	b.mouse_entered.connect(b.grab_focus)
	var v := VBoxContainer.new()
	v.set_anchors_preset(Control.PRESET_FULL_RECT)
	v.offset_left = 24
	v.offset_top = 10
	v.offset_right = -24
	v.add_theme_constant_override("separation", 2)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var top := HBoxContainer.new()
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var name_label := _label("Empty slot" if empty else Saves.label_of(e), 32, DIM if empty else GOLD, true)
	name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(name_label)
	if not empty:
		top.add_child(_label("%s  ·  %s" % [Locations.title(main.data.config, e.location), e.get("when", "")], 24, DIM, true))
	v.add_child(top)
	var sub := _label("" if empty else Saves.quest_line(e), 24, INK, true)
	sub.clip_text = true
	sub.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	v.add_child(sub)
	b.add_child(v)
	return b


func _scrolled(content: Control, count: int) -> ScrollContainer:
	var s := ScrollContainer.new()
	s.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	s.follow_focus = true
	s.custom_minimum_size = Vector2(1390, mini(count, 8) * 108)
	content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	s.add_child(content)
	return s


# ---------- settings ----------

func _screen_settings() -> void:
	var box := _panel_box(1380)
	box.add_child(_heading("SETTINGS"))
	box.add_child(_section("SOUND"))
	_volume_row(box, "Master volume", "master")
	_volume_row(box, "Voices", "voice")
	_volume_row(box, "Ambience", "ambience")
	_volume_row(box, "Effects", "effects")
	_volume_row(box, "Music", "music")
	box.add_child(_section("TEXT"))
	_cycle_row(box, "Text speed", "text_speed", TEXT_SPEEDS, ["Instant", "Fast", "Normal", "Slow"])
	_cycle_row(box, "Auto-advance", "auto_advance", [true, false], ["On: lines follow each other", "Off: press to go on"])
	box.add_child(_section("DISPLAY"))
	_cycle_row(box, "Fullscreen", "fullscreen", [false, true], ["Windowed", "Fullscreen"])
	_cycle_row(box, "Hints", "hints", HINTS, ["Automatic", "Mouse and keys", "Controller"])
	box.add_child(_gap(8))
	_button("Back", _back, box)


func _volume_row(parent: Control, text: String, key: String) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 26)
	var name_label := _label(text, 30, INK)
	name_label.custom_minimum_size = Vector2(420, 0)
	var s := HSlider.new()
	s.min_value = 0
	s.max_value = 100
	s.step = 5
	s.value = roundf(Settings.volume(key) * 100.0)
	s.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	s.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	s.custom_minimum_size = Vector2(0, 44)
	var num := _label("%d%%" % int(s.value), 28, DIM)
	num.custom_minimum_size = Vector2(90, 0)
	num.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	s.value_changed.connect(func(v):
		Settings.set_value(key, v / 100.0)
		num.text = "%d%%" % int(v)
		if key == "ambience":
			main.audio.refresh())
	s.focus_entered.connect(func(): name_label.add_theme_color_override("font_color", GOLD_HOT))
	s.focus_exited.connect(func(): name_label.remove_theme_color_override("font_color"))
	row.add_child(name_label)
	row.add_child(s)
	row.add_child(num)
	var indent := MarginContainer.new()
	indent.add_theme_constant_override("margin_left", 22)
	indent.add_child(row)
	parent.add_child(indent)
	if _first == null:
		_first = s


## A setting with a few values: Enter or a click steps on, Left and Right step either way.
func _cycle_row(parent: Control, text: String, key: String, options: Array, labels: Array) -> void:
	var b := Button.new()
	b.custom_minimum_size = Vector2(0, 62)
	b.focus_mode = Control.FOCUS_ALL
	var h := HBoxContainer.new()
	h.set_anchors_preset(Control.PRESET_FULL_RECT)
	h.offset_left = 22
	h.offset_right = -22
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var name_label := _label(text, 30, INK, true)
	name_label.custom_minimum_size = Vector2(420, 0)
	name_label.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var value := _label("", 30, GOLD, true)
	value.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	h.add_child(name_label)
	h.add_child(value)
	b.add_child(h)
	var step := func(dir: int):
		var i := options.find(Settings.get_value(key))
		Settings.set_value(key, options[posmod(i + dir, options.size())])
		value.text = labels[options.find(Settings.get_value(key))]
		_refresh_hint()
	value.text = labels[maxi(options.find(Settings.get_value(key)), 0)]
	b.pressed.connect(func(): step.call(1))
	b.gui_input.connect(func(ev: InputEvent):
		if ev.is_action_pressed("ui_left"):
			step.call(-1)
			b.accept_event()
		elif ev.is_action_pressed("ui_right"):
			step.call(1)
			b.accept_event())
	b.mouse_entered.connect(b.grab_focus)
	parent.add_child(b)


# ---------- the parts ----------

func _panel_box(width: int) -> VBoxContainer:
	panel.custom_minimum_size = Vector2(width, 0)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 18)
	panel.add_child(box)
	return box


func _heading(text: String) -> Control:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	box.add_child(_label(text, 26, GOLD))
	box.add_child(_rule(0))
	return box


## A small heading over a group of settings, with a little air above it.
func _section(text: String) -> Control:
	var m := MarginContainer.new()
	m.add_theme_constant_override("margin_top", 12)
	m.add_child(_label(text, 21, Color(GOLD, 0.7), true))
	return m


func _label(text: String, size: int, color: Color, ignore_mouse := false) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	if ignore_mouse:
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func _wrap(text: String, size: int, color: Color, width: int) -> Label:
	var l := _label(text, size, color)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(width, 0)
	return l


## A small dim line under a button, lined up with the button's text.
func _note(text: String) -> Control:
	var m := MarginContainer.new()
	m.add_theme_constant_override("margin_left", 28)
	m.add_child(_label(text, 22, DIM, true))
	return m


func _rule(width: int) -> ColorRect:
	var r := ColorRect.new()
	r.color = Color(BRASS, 0.5 if width > 0 else 0.35)
	r.custom_minimum_size = Vector2(width, 1)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r


func _gap(h: int) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(0, h)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return c


## A button of the left column; the pointer moving over it focuses it.
func _item(text: String, on_press: Callable) -> Button:
	var b := _button(text, on_press, column)
	b.add_theme_font_size_override("font_size", 44)
	return b


func _button(text: String, on_press: Callable, parent: Control) -> Button:
	var b := Button.new()
	b.text = text
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.focus_mode = Control.FOCUS_ALL
	b.pressed.connect(on_press)
	b.mouse_entered.connect(func():
		if not b.disabled:
			b.grab_focus())
	parent.add_child(b)
	if _first == null:
		_first = b
	return b


## A line for a moment at the bottom of the screen.
func say(text: String) -> void:
	status.text = text
	if _status_tween:
		_status_tween.kill()
	_status_tween = create_tween()
	_status_tween.tween_property(status, "modulate:a", 1.0, 0.15)
	_status_tween.tween_interval(2.4)
	_status_tween.tween_property(status, "modulate:a", 0.0, 0.6)


func _refresh_hint() -> void:
	_hint_pad = Settings.pad_hints(main.pad != null and main.pad.active)
	var parts: Array[String] = []
	parts.append("D-pad  move" if _hint_pad else "Up Down  move")
	if screen in ["settings", "new_game"]:
		parts.append("D-pad left right  adjust" if _hint_pad else "Left Right  adjust")
	parts.append("A  confirm" if _hint_pad else "Enter  confirm")
	if screen != "title":
		parts.append("B  back" if _hint_pad else "Esc  back")
	hint.text = "     ".join(parts)


# ---------- theme ----------

func _make_theme() -> Theme:
	var t := Theme.new()
	t.default_font = font
	t.default_font_size = 30
	t.set_color("font_color", "Label", INK)
	# buttons: no box until focused (the pointer moving over one focuses it), then a brass bar
	var none := StyleBoxEmpty.new()
	var lit := StyleBoxFlat.new()
	lit.bg_color = Color(BRASS, 0.16)
	lit.border_width_left = 4
	lit.border_color = GOLD
	for s in [none, lit]:
		s.content_margin_left = 24
		s.content_margin_right = 24
		s.content_margin_top = 8
		s.content_margin_bottom = 8
	for n in ["normal", "hover", "pressed", "disabled", "hover_pressed"]:
		t.set_stylebox(n, "Button", none)
	t.set_stylebox("focus", "Button", lit)
	t.set_color("font_color", "Button", INK)
	t.set_color("font_hover_color", "Button", INK)
	t.set_color("font_focus_color", "Button", GOLD_HOT)
	t.set_color("font_pressed_color", "Button", GOLD_HOT)
	t.set_color("font_hover_pressed_color", "Button", GOLD_HOT)
	t.set_color("font_disabled_color", "Button", Color(DIM, 0.45))
	t.set_font_size("font_size", "Button", 34)
	# sliders: a brass groove filled with gold up to a round grabber
	var groove := StyleBoxFlat.new()
	groove.bg_color = Color(BRASS, 0.3)
	groove.set_corner_radius_all(3)
	groove.content_margin_top = 3
	groove.content_margin_bottom = 3
	var filled := StyleBoxFlat.new()
	filled.bg_color = Color(GOLD, 0.8)
	filled.set_corner_radius_all(3)
	filled.content_margin_top = 3
	filled.content_margin_bottom = 3
	var ring := StyleBoxFlat.new()
	ring.draw_center = false
	ring.border_color = Color(GOLD, 0.55)
	ring.set_border_width_all(1)
	ring.set_corner_radius_all(4)
	t.set_stylebox("slider", "HSlider", groove)
	t.set_stylebox("grabber_area", "HSlider", filled)
	t.set_stylebox("grabber_area_highlight", "HSlider", filled)
	t.set_stylebox("focus", "HSlider", ring)
	t.set_icon("grabber", "HSlider", _dot(13, GOLD))
	t.set_icon("grabber_highlight", "HSlider", _dot(15, GOLD_HOT))
	t.set_icon("grabber_disabled", "HSlider", _dot(13, DIM))
	var tick := Image.create(2, 16, false, Image.FORMAT_RGBA8)
	tick.fill(Color(BRASS, 0.8))
	t.set_icon("tick", "HSlider", ImageTexture.create_from_image(tick))
	# the name field of the save screen
	var field := StyleBoxFlat.new()
	field.bg_color = Color(0.07, 0.065, 0.06)
	field.border_color = Color(BRASS, 0.6)
	field.set_border_width_all(1)
	field.content_margin_left = 18
	field.content_margin_right = 18
	var field_hot := field.duplicate()
	field_hot.border_color = GOLD
	t.set_stylebox("normal", "LineEdit", field)
	t.set_stylebox("focus", "LineEdit", field_hot)
	t.set_color("font_color", "LineEdit", INK)
	t.set_color("caret_color", "LineEdit", GOLD)
	t.set_color("selection_color", "LineEdit", Color(BRASS, 0.5))
	t.set_font_size("font_size", "LineEdit", 32)
	# scrolling lists: a thin brass bar
	var track := StyleBoxEmpty.new()
	track.content_margin_left = 6
	track.content_margin_right = 6
	t.set_stylebox("scroll", "VScrollBar", track)
	for pair in [["grabber", 0.4], ["grabber_highlight", 0.7], ["grabber_pressed", 0.9]]:
		var g := StyleBoxFlat.new()
		g.bg_color = Color(BRASS, pair[1])
		g.set_corner_radius_all(2)
		g.content_margin_left = 6
		g.content_margin_right = 6
		t.set_stylebox(pair[0], "VScrollBar", g)
	return t


static func _dot(radius: int, color: Color) -> ImageTexture:
	var d := radius * 2 + 2
	var img := Image.create(d, d, false, Image.FORMAT_RGBA8)
	for y in d:
		for x in d:
			var r := Vector2(x + 0.5 - d * 0.5, y + 0.5 - d * 0.5).length()
			img.set_pixel(x, y, Color(color, clampf(radius + 0.5 - r, 0.0, 1.0)))
	return ImageTexture.create_from_image(img)
