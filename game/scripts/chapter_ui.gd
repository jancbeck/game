## The end of a chapter. The story calls `end_chapter("<id>")` (dialogue.gd); the screen fades to
## black, a card shows the chapter's title and closing words, a second page lists what the player
## did (the story variables and the skill checks named in data/chapters.json), and the game goes back
## to the title screen. The game is saved to the autosave slot at the card; a save that holds the
## card (`chapter_end` in session.gd) loads to it again, and the title's Continue is off for it.
##
##   main.chapter.begin("night_one")      main.chapter.active      main.chapter.page  # "", "card", "summary"
extends CanvasLayer

const Chapters := preload("res://scripts/chapters.gd")
const Saves := preload("res://scripts/saves.gd")
const Settings := preload("res://scripts/settings.gd")

const INK := Color(0.86, 0.83, 0.76)
const GOLD := Color("#d9b77a")
const GOLD_HOT := Color("#f2dcae")
const DIM := Color(0.62, 0.59, 0.54)
const BRASS := Color(0.55, 0.45, 0.3)
const PANEL_BG := Color(0.035, 0.035, 0.04)
const FAILED := "#c8553d"
const MAX_CHECKS := 12

static var fade_s := 1.4         # the world goes dark
static var dwell_s := 2.4        # the card stands this long before Continue appears

var main
var chapters
var active := false
var page := ""                   # "card", "summary" or "" (nothing shown)
var chapter_id := ""
var font: SystemFont
var title_font: FontVariation
var root: Control
var card_page: Control
var summary_page: Control
var card_button: Button
var summary_button: Button
var _tween: Tween


func setup(m, ui_font: SystemFont) -> void:
	main = m
	font = ui_font
	layer = 11
	chapters = Chapters.new()
	chapters.load_file(main.data.config.get("chapters", "data/chapters.json"))
	title_font = FontVariation.new()
	var serif := SystemFont.new()
	serif.font_names = PackedStringArray(["Baskerville", "Hoefler Text", "Didot", "Georgia", "serif"])
	serif.antialiasing = TextServer.FONT_ANTIALIASING_GRAY
	title_font.base_font = serif
	title_font.spacing_glyph = 14
	root = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_STOP
	root.theme = main.menu.ui_theme()
	root.visible = false
	add_child(root)
	var back := ColorRect.new()
	back.color = Color.BLACK
	back.set_anchors_preset(Control.PRESET_FULL_RECT)
	back.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(back)


# ---------- the sequence ----------

## Ends the chapter: fades out, saves, shows the card. `loaded` is a world built from a save that
## holds the card: it is dark already and is not saved again. False for a chapter the data lacks.
func begin(id: String, loaded := false) -> bool:
	if active:
		return false
	if not chapters.has(id):
		push_error("end_chapter: no chapter '%s' in data/chapters.json" % id)
		return false
	active = true
	chapter_id = id
	main.ui.busy = true
	main.player.stop()
	if not loaded:
		await main.ui.fade_to(1.0, fade_s)
		main.ui.close()
		main.session.chapter_end = id
		main.session.save(Saves.AUTO, chapters.title(id))
	main.ui.fade.modulate.a = 1.0
	root.visible = true
	_build_card()
	await _show(card_page, 1.2)
	page = "card"
	await get_tree().create_timer(dwell_s).timeout
	if page == "card":
		card_button.visible = true
		card_button.grab_focus()
	return true


func _on_continue() -> void:
	if page != "card":
		return
	page = ""
	await _hide(card_page, 0.6)
	_build_summary()
	await _show(summary_page, 0.9)
	page = "summary"
	summary_button.grab_focus()


func _on_leave() -> void:
	if page != "summary":
		return
	page = ""
	main.session.to_title()


## Fades `p` in; the page before it is gone.
func _show(p: Control, seconds: float) -> void:
	p.modulate.a = 0.0
	p.visible = true
	_tween = create_tween()
	_tween.tween_property(p, "modulate:a", 1.0, seconds)
	await _tween.finished


func _hide(p: Control, seconds: float) -> void:
	_tween = create_tween()
	_tween.tween_property(p, "modulate:a", 0.0, seconds)
	await _tween.finished
	p.queue_free()


# ---------- the card ----------

func _build_card() -> void:
	var def: Dictionary = chapters.def(chapter_id)
	card_page = _centered()
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 30)
	box.alignment = BoxContainer.ALIGNMENT_CENTER
	card_page.add_child(box)
	box.add_child(_label(main.menu.NAME.to_upper(), 24, DIM, HORIZONTAL_ALIGNMENT_CENTER))
	box.add_child(_rule(110))
	var title := _label(String(def.get("title", chapter_id)).to_upper(), 84, GOLD, HORIZONTAL_ALIGNMENT_CENTER, 1900)
	title.add_theme_font_override("font", title_font)
	title.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.7))
	title.add_theme_constant_override("shadow_offset_y", 5)
	box.add_child(title)
	box.add_child(_rule(640))
	if str(def.get("body", "")) != "":
		box.add_child(_label(def.body, 34, INK, HORIZONTAL_ALIGNMENT_CENTER, 1200))
	box.add_child(_gap(36))
	card_button = _button("Continue", _on_continue)
	card_button.visible = false
	box.add_child(card_button)


# ---------- what the player did ----------

func _build_summary() -> void:
	var def: Dictionary = chapters.def(chapter_id)
	var sm: Dictionary = def.get("summary", {})
	summary_page = _centered()
	var panel := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(PANEL_BG, 0.95)
	sb.border_color = Color(BRASS, 0.5)
	sb.set_border_width_all(1)
	sb.border_width_top = 2
	sb.content_margin_left = 56
	sb.content_margin_right = 56
	sb.content_margin_top = 38
	sb.content_margin_bottom = 34
	panel.add_theme_stylebox_override("panel", sb)
	panel.custom_minimum_size = Vector2(1700, 0)
	summary_page.add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 14)
	panel.add_child(box)
	box.add_child(_label(String(sm.get("title", "What you did")).to_upper(), 26, GOLD))
	box.add_child(_rule(0))
	for r in Chapters.rows(def, func(name): return main.quest.get_flag(name, "")):
		box.add_child(_row(r.label, r.text))
	var made: Array = Chapters.checks(main.skills.rolls)
	if sm.has("checks") and not made.is_empty():
		box.add_child(_gap(10))
		box.add_child(_label(String(sm.checks).to_upper(), 22, Color(GOLD, 0.7)))
		for c in made.slice(0, MAX_CHECKS):
			box.add_child(_check_row(c))
		if made.size() > MAX_CHECKS:
			box.add_child(_label("and %d more" % (made.size() - MAX_CHECKS), 24, DIM))
	box.add_child(_rule(0))
	if str(sm.get("next", "")) != "":
		box.add_child(_label(sm.next, 26, DIM))
	summary_button = _button("Back to the title", _on_leave)
	summary_button.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	box.add_child(summary_button)


func _row(label: String, text: String) -> Control:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 40)
	var l := _label(label.to_upper(), 24, GOLD)
	l.custom_minimum_size = Vector2(480, 0)
	l.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	h.add_child(l)
	h.add_child(_label(text, 30, INK, HORIZONTAL_ALIGNMENT_LEFT, 1050))
	return h


## `SKILL [Difficulty n, white or red]  Passed`: the skill in its colour, the bracket as in the log.
func _check_row(c: Dictionary) -> Control:
	var sk = main.skills
	var r := RichTextLabel.new()
	r.bbcode_enabled = true
	r.fit_content = true
	r.scroll_active = false
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	r.add_theme_font_override("normal_font", font)
	r.add_theme_font_size_override("normal_font_size", 28)
	r.add_theme_color_override("default_color", INK)
	var kind_color: String = main.ui.RED_CHECK if c.kind == "red" else main.ui.WHITE_CHECK
	r.text = "[color=#%s]%s[/color]  [color=%s][lb]%s %d, %s[rb][/color]  [color=%s]%s[/color]" % [
		sk.color_of(c.skill).to_html(false), sk.skill_name(c.skill).to_upper(), kind_color,
		sk.difficulty_name(c.dc), c.dc, c.kind, "#%s" % INK.to_html(false) if c.success else FAILED,
		"Passed" if c.success else "Failed"]
	return r


# ---------- the parts ----------

func _centered() -> Control:
	var c := CenterContainer.new()
	c.set_anchors_preset(Control.PRESET_FULL_RECT)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	c.visible = false
	root.add_child(c)
	return c


func _label(text: String, size: int, color: Color, align := HORIZONTAL_ALIGNMENT_LEFT, width := 0) -> Label:
	var l := Label.new()
	l.text = text
	l.horizontal_alignment = align
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if width > 0:
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.custom_minimum_size = Vector2(width, 0)
	return l


func _rule(width: int) -> Control:
	var r := ColorRect.new()
	r.color = Color(BRASS, 0.5 if width > 0 else 0.35)
	r.custom_minimum_size = Vector2(width, 1)
	r.size_flags_horizontal = Control.SIZE_SHRINK_CENTER if width > 0 else Control.SIZE_FILL
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r


func _gap(h: int) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(0, h)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return c


func _button(text: String, on_press: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	b.focus_mode = Control.FOCUS_ALL
	b.add_theme_font_size_override("font_size", 40)
	b.pressed.connect(on_press)
	b.mouse_entered.connect(b.grab_focus)
	return b
