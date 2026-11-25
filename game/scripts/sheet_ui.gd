## The character sheet (C, the pad's View button) and the journal (J, RB): one panel in the style of
## the dialogue column and the satchel (dark, brass rule, serif). The sheet lists the six skills
## with their values and what each is for; the journal lists the open tasks and then the closed
## ones, each with the text the story last gave it. While the panel is open the dialogue column
## takes no input (ui.suspended), so a check can be weighed without a response being picked.
extends CanvasLayer

const Settings := preload("res://scripts/settings.gd")

const INK := Color(0.86, 0.83, 0.76)
const DIM := Color(0.62, 0.59, 0.54)
const BRASS := Color(0.55, 0.45, 0.3)
const GOLD := Color("#d9b77a")
const PANEL_W := 1200

var main
var font: SystemFont
var panel: PanelContainer
var title: Label
var sheet_box: VBoxContainer
var journal_text: RichTextLabel
var reach: Label
var hint: Label
var mode := "sheet"
var selected := 0
var _rows: Array[Dictionary] = []     # {panel, style, value, name, text}


func setup(m, ui_font: SystemFont) -> void:
	main = m
	font = ui_font
	layer = 9
	panel = PanelContainer.new()
	panel.anchor_left = 0.0
	panel.anchor_right = 0.0
	panel.anchor_top = 0.5
	panel.anchor_bottom = 0.5
	panel.offset_left = 300
	panel.offset_right = 300 + PANEL_W
	panel.grow_vertical = Control.GROW_DIRECTION_BOTH
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.035, 0.035, 0.04, 0.93)
	sb.border_color = Color(BRASS, 0.5)
	sb.set_border_width_all(1)
	sb.border_width_top = 2
	sb.content_margin_left = 40
	sb.content_margin_right = 40
	sb.content_margin_top = 30
	sb.content_margin_bottom = 26
	panel.add_theme_stylebox_override("panel", sb)
	panel.visible = false
	add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 16)
	panel.add_child(box)
	title = _label(24, GOLD)
	box.add_child(title)
	box.add_child(_rule())

	sheet_box = VBoxContainer.new()
	sheet_box.add_theme_constant_override("separation", 6)
	box.add_child(sheet_box)
	for i in main.skills.defs.size():
		_rows.append(_make_row(i))
	reach = _label(24, DIM)
	reach.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	reach.custom_minimum_size = Vector2(PANEL_W - 80, 0)
	sheet_box.add_child(reach)

	journal_text = RichTextLabel.new()
	journal_text.bbcode_enabled = true
	journal_text.add_theme_font_override("normal_font", font)
	journal_text.add_theme_font_size_override("normal_font_size", 27)
	journal_text.add_theme_color_override("default_color", INK)
	journal_text.add_theme_constant_override("line_separation", 5)
	journal_text.custom_minimum_size = Vector2(PANEL_W - 80, 760)
	journal_text.visible = false
	box.add_child(journal_text)

	box.add_child(_rule())
	hint = _label(22, DIM)
	box.add_child(hint)
	main.skills.changed.connect(func(_id): _refresh())
	main.journal.changed.connect(func(_id): _refresh())


func _label(size: int, color: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_override("font", font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func _rule() -> ColorRect:
	var r := ColorRect.new()
	r.color = Color(BRASS, 0.35)
	r.custom_minimum_size = Vector2(0, 1)
	return r


func _make_row(i: int) -> Dictionary:
	var p := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.set_content_margin_all(14)
	style.set_corner_radius_all(3)
	p.add_theme_stylebox_override("panel", style)
	p.mouse_filter = Control.MOUSE_FILTER_STOP
	p.mouse_entered.connect(func(): select(i))
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 26)
	p.add_child(h)
	var v := _label(68, INK)
	v.custom_minimum_size = Vector2(90, 0)
	v.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	h.add_child(v)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 2)
	h.add_child(col)
	var n := _label(32, INK)
	col.add_child(n)
	var t := _label(25, DIM)
	t.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	t.custom_minimum_size = Vector2(PANEL_W - 80 - 90 - 26 - 28, 0)
	col.add_child(t)
	sheet_box.add_child(p)
	return {panel = p, style = style, value = v, name = n, text = t}


# ---------- opening ----------

func is_open() -> bool:
	return panel != null and panel.visible


## "sheet" or "journal"; the key of the one that is showing closes it, the other switches.
func toggle(which := "sheet") -> void:
	if is_open() and mode == which:
		close()
	else:
		open(which)


func open(which := "sheet") -> void:
	mode = which
	main.inventory_ui.close()
	main.ui.hover.visible = false
	main.ui.suspended = true
	panel.visible = true
	_refresh()


func close() -> void:
	if is_open():
		panel.visible = false
		main.ui.suspended = false


## Pad up/down and the arrow keys: the next skill, or a scroll of the journal.
func move(step: int) -> void:
	if mode == "sheet":
		select(posmod(selected + step, maxi(_rows.size(), 1)))
	else:
		var bar := journal_text.get_v_scroll_bar()
		bar.value += step * 110


func select(i: int) -> void:
	if i != selected:
		selected = i
		_refresh()


func _unhandled_input(event: InputEvent) -> void:
	if is_open() and event is InputEventKey and event.pressed:
		if event.keycode == KEY_DOWN:
			move(1)
		elif event.keycode == KEY_UP:
			move(-1)


# ---------- content ----------

func _refresh() -> void:
	if not is_open():
		return
	var sheet := mode == "sheet"
	title.text = "CHARACTER" if sheet else "JOURNAL"
	sheet_box.visible = sheet
	journal_text.visible = not sheet
	if sheet:
		_refresh_sheet()
	else:
		journal_text.text = journal_bbcode()
	var pad := Settings.pad_hints(main.pad != null and main.pad.active)
	hint.text = ("View  character     RB  journal     B  close" if pad else "C  character     J  journal     Esc  close")


func _refresh_sheet() -> void:
	var sk = main.skills
	for i in _rows.size():
		var d: Dictionary = sk.defs[i]
		var r: Dictionary = _rows[i]
		var c := Color(d.color)
		r.value.text = str(sk.value(d.id))
		r.value.add_theme_color_override("font_color", c)
		r.name.text = String(d.name).to_upper()
		r.name.add_theme_color_override("font_color", c)
		r.text.text = d.get("description", "")
		var hot := i == selected
		r.style.bg_color = Color(c, 0.14) if hot else Color(0.09, 0.085, 0.08, 0.0)
		r.style.border_color = Color(c, 0.7) if hot else Color(0, 0, 0, 0)
		r.style.set_border_width_all(1 if hot else 0)
	var cur: Dictionary = sk.defs[selected]
	var passive: int = sk.value(cur.id) + sk.PASSIVE_BONUS
	reach.text = "Speaks up unasked for anything up to %s (%d). When rolled: two dice plus %d." % [
		sk.difficulty_name(passive), passive, sk.value(cur.id)]


## The journal as text: open tasks, then closed ones, the latest touched first.
func journal_bbcode() -> String:
	var j = main.journal
	var parts: Array[String] = []
	for done in [false, true]:
		var list: Array = j.list(done)
		if list.is_empty():
			continue
		parts.append("[font_size=22][color=%s]%s[/color][/font_size]" % [("#d9b77a" if not done else "#7d786f"), "OPEN" if not done else "DONE"])
		for e in list:
			if done:
				parts.append("[color=#7d786f]%s\n%s[/color]" % [j.title(e.id).to_upper(), e.text])
			else:
				parts.append("[color=#e8c98f]%s[/color]\n%s" % [j.title(e.id).to_upper(), e.text])
	if parts.is_empty():
		return "[color=#7d786f]Nothing written down yet.[/color]"
	return "\n\n".join(parts)
