## Hover name near the cursor, and a dialogue column on the right in the manner of Disco Elysium:
## a dark scrolling log of plain serif text, the speaker in capitals, numbered responses below.
## In a conversation a small portrait of the speaker sits at the top of the column.
##
## A response is a string, or a dictionary for a skill check: {text, tag, tag_color, locked}. The tag
## ("Bearing · Challenging 12 · 58%", the chance in bold) and the text are drawn white for a white
## check and red for a red one (tag_color is WHITE_CHECK or RED_CHECK); a locked response is greyed
## and struck through and cannot be picked by key, pad or mouse.
##
## The log: the newest entry is at full brightness, the ones before it fade to a dim grey (FADE);
## a new entry appears at the player's text speed (settings.gd; `revealing()` is true meanwhile)
## and the log glides down to it. A click on the log asks for the next line (`advance_requested`),
## the wheel and Page Up / Page Down scroll it. A dim line under the responses names what the mouse
## and keys do, or the controller's buttons (settings.gd: hints), for the moment the column is in.
extends CanvasLayer

const Settings := preload("res://scripts/settings.gd")

signal closed
signal advance_requested

const INK := Color(0.86, 0.83, 0.76)
const SPEAKER := "#d9b77a"
const OPTION := "#c8553d"
const OPTION_HOT := "#f08a6a"
const DIM := Color(0.54, 0.52, 0.49)
const WHITE_CHECK := "#f7f4ea"          # the bracket of a white check; its text is a little softer
const WHITE_TEXT := "#d9d4c7"
const WHITE_TEXT_HOT := "#ffffff"
const RED_CHECK := "#ff3a2e"
const RED_TEXT := "#ee4337"
const RED_TEXT_HOT := "#ff8070"
const LOCKED_TEXT := "#67625a"
const LOCKED_WHITE := "#8c887e"
const LOCKED_RED := "#93403a"
const BRASS := Color(0.55, 0.45, 0.3)
const PANEL_BG := Color(0.035, 0.035, 0.04)
## How much of its colour an entry keeps, by how many entries ago it was written: the newest all of
## it, the one before a little less, from the fourth on the grey the log always had.
const FADE := [1.0, 0.8, 0.7, 0.62]
const SCROLL_S := 0.35
## The column's width and its distance from the screen edge (canvas px); notices keep out of it.
const COLUMN_W := 640
const COLUMN_EDGE := 40

var font: SystemFont
var font_bold: FontVariation
var hover: Label
var panel: PanelContainer
var log_text: RichTextLabel
var option: RichTextLabel
var hint_label: Label
var history: Array[Dictionary] = []   # {head, color, bracket, bracket_color, text}
var fade: ColorRect
var card: Label
var busy := false
var tags: Array[Label] = []
var portrait: TextureRect
var choices: Array = []           # responses (see above); empty = the single [Leave.] of a look-text
var suspended := false            # a panel (character sheet, journal) is open over the column: no picking
var pad_mode := false             # a controller is in use: the first response is highlighted
var _on_choice: Callable
var _hint_pad := false
var _hot := -1
var _reveal_pos := -1.0           # characters of the log shown so far while the newest entry appears; -1 when done
var _reveal_total := 0
var _scroll_tween: Tween
var _following := false


func _ready() -> void:
	layer = 10
	font = SystemFont.new()
	font.font_names = PackedStringArray(["Georgia", "Baskerville", "Libre Baskerville", "Times New Roman", "serif"])
	font.antialiasing = TextServer.FONT_ANTIALIASING_GRAY
	font_bold = FontVariation.new()
	font_bold.base_font = font
	font_bold.variation_embolden = 0.7

	hover = Label.new()
	hover.add_theme_font_override("font", font)
	hover.add_theme_font_size_override("font_size", 28)
	hover.add_theme_color_override("font_color", INK)
	hover.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	hover.add_theme_constant_override("outline_size", 8)
	hover.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hover.visible = false
	add_child(hover)

	panel = PanelContainer.new()
	panel.anchor_left = 1.0
	panel.anchor_right = 1.0
	panel.anchor_top = 0.0
	panel.anchor_bottom = 1.0
	panel.offset_left = -(COLUMN_W + COLUMN_EDGE)
	panel.offset_right = -COLUMN_EDGE
	panel.offset_top = 40
	panel.offset_bottom = -40
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.035, 0.035, 0.04, 0.88)
	sb.border_color = Color(0.55, 0.45, 0.3, 0.5)
	sb.border_width_left = 2
	sb.content_margin_left = 30
	sb.content_margin_right = 26
	sb.content_margin_top = 28
	sb.content_margin_bottom = 26
	panel.add_theme_stylebox_override("panel", sb)
	panel.visible = false
	add_child(panel)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 22)
	panel.add_child(box)
	portrait = TextureRect.new()
	portrait.custom_minimum_size = Vector2(240, 240)
	portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	portrait.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	portrait.visible = false
	box.add_child(portrait)
	log_text = _rich(27)
	log_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	log_text.gui_input.connect(_on_log_input)
	_style_scrollbar(log_text.get_v_scroll_bar())
	log_text.add_child(_top_fade())
	box.add_child(log_text)
	var rule := ColorRect.new()
	rule.color = Color(0.55, 0.45, 0.3, 0.35)
	rule.custom_minimum_size = Vector2(0, 1)
	box.add_child(rule)
	option = _rich(27)
	option.fit_content = true
	option.mouse_filter = Control.MOUSE_FILTER_STOP
	option.meta_underlined = false
	option.meta_clicked.connect(func(meta): _pick(int(str(meta))))
	option.meta_hover_started.connect(func(meta): _hot = int(str(meta)); _draw_option())
	option.meta_hover_ended.connect(func(_meta): _hot = -1; _draw_option())
	box.add_child(option)
	hint_label = Label.new()
	hint_label.add_theme_font_override("font", font)
	hint_label.add_theme_font_size_override("font_size", 20)
	hint_label.add_theme_color_override("font_color", DIM)
	hint_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	box.add_child(hint_label)

	fade = ColorRect.new()
	fade.color = Color.BLACK
	fade.set_anchors_preset(Control.PRESET_FULL_RECT)
	fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	fade.modulate.a = 0.0
	add_child(fade)
	card = Label.new()
	card.set_anchors_preset(Control.PRESET_FULL_RECT)
	card.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	card.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	card.add_theme_font_override("font", font)
	card.add_theme_font_size_override("font_size", 60)
	card.add_theme_color_override("font_color", INK)
	card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	card.modulate.a = 0.0
	add_child(card)


func _rich(size: int) -> RichTextLabel:
	var r := RichTextLabel.new()
	r.bbcode_enabled = true
	r.add_theme_font_override("normal_font", font)
	r.add_theme_font_override("bold_font", font_bold)
	r.add_theme_font_size_override("normal_font_size", size)
	r.add_theme_font_size_override("bold_font_size", size)
	r.add_theme_color_override("default_color", INK)
	r.add_theme_constant_override("line_separation", 5)
	return r


## The log's scroll bar: thin and brass.
func _style_scrollbar(bar: VScrollBar) -> void:
	var none := StyleBoxEmpty.new()
	none.content_margin_left = 5
	none.content_margin_right = 5
	bar.add_theme_stylebox_override("scroll", none)
	bar.add_theme_stylebox_override("scroll_focus", none)
	for pair in [["grabber", 0.4], ["grabber_highlight", 0.7], ["grabber_pressed", 0.9]]:
		var g := StyleBoxFlat.new()
		g.bg_color = Color(BRASS, pair[1])
		g.set_corner_radius_all(2)
		g.content_margin_left = 5
		g.content_margin_right = 5
		bar.add_theme_stylebox_override(pair[0], g)


## The log's top edge: what scrolls away fades out.
func _top_fade() -> TextureRect:
	var grad := Gradient.new()
	grad.set_color(0, Color(PANEL_BG, 0.7))
	grad.set_color(1, Color(PANEL_BG, 0.0))
	var tex := GradientTexture2D.new()
	tex.gradient = grad
	tex.fill_from = Vector2(0, 0)
	tex.fill_to = Vector2(0, 1)
	tex.width = 4
	tex.height = 48
	var r := TextureRect.new()
	r.texture = tex
	r.stretch_mode = TextureRect.STRETCH_SCALE
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.anchor_right = 1.0
	r.offset_right = -14
	r.offset_bottom = 48
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r


func show_hover(text: String, pos: Vector2) -> void:
	hover.visible = text != "" and not panel.visible
	if hover.visible:
		hover.text = text
		hover.reset_size()
		var vp := get_viewport().get_visible_rect().size
		hover.position = (pos + Vector2(18, 14)).clamp(Vector2.ZERO, vp - hover.size)


## Names of every interactable at their screen positions (while Tab is held); [] hides them.
func show_tags(items: Array) -> void:
	while tags.size() < items.size():
		var l := Label.new()
		l.add_theme_font_override("font", font)
		l.add_theme_font_size_override("font_size", 22)
		l.add_theme_color_override("font_color", Color(INK, 0.85))
		l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
		l.add_theme_constant_override("outline_size", 7)
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(l)
		move_child(l, 0)
		tags.append(l)
	for i in tags.size():
		var on := i < items.size() and not panel.visible
		tags[i].visible = on
		if on:
			tags[i].text = items[i][0]
			tags[i].reset_size()
			tags[i].position = items[i][1] - Vector2(tags[i].size.x * 0.5, tags[i].size.y + 6)


## A line in the log; without a speaker it is narration.
func say(speaker: String, text: String) -> void:
	_log({head = speaker.to_upper(), color = SPEAKER, text = text})


## A skill speaking, or a roll: `NAME [bracket] — text`, the name in the skill's colour and the
## bracket (the difficulty and result) in white or red after the kind of check.
func say_skill(skill_name: String, color: Color, bracket: String, bracket_color: String, text: String) -> void:
	_log({head = skill_name.to_upper(), color = "#" + color.to_html(false), bracket = bracket,
		bracket_color = bracket_color, text = text, voice = color.lerp(Color(INK), 0.4)})


## What the mouse and keys do now, or the controller's buttons: responses to pick, or the next line to ask for.
func _refresh_hint() -> void:
	_hint_pad = Settings.pad_hints(pad_mode)
	if option.visible and not choices.is_empty():
		hint_label.text = "D-pad  choose        A  answer        B  leave" if _hint_pad \
			else "Click or 1-%d  answer        Esc  leave" % mini(choices.size(), 9)
	elif option.visible:
		hint_label.text = "A or B  leave" if _hint_pad else "Click or Esc  leave"
	else:
		hint_label.text = "A  next line" if _hint_pad else "Click or Space  next line"


func _log(entry: Dictionary) -> void:
	history.append(entry)
	_rebuild_log()
	_start_reveal(entry)
	_draw_option()
	panel.visible = true
	hover.visible = false
	_follow()


func _rebuild_log() -> void:
	var parts: Array[String] = []
	for i in history.size():
		parts.append(_entry_bbcode(history[i], history.size() - 1 - i))
	log_text.visible_characters = -1
	log_text.text = "\n\n".join(parts)


## The colour an entry has `age` entries after it was written.
static func faded(color: Color, age: int) -> Color:
	return PANEL_BG.lerp(color, FADE[mini(age, FADE.size() - 1)])


func _entry_bbcode(e: Dictionary, age: int) -> String:
	var body := "[color=#%s]%s[/color]" % [faded(e.get("voice", INK), age).to_html(false), e.text]
	if e.head == "":
		return body
	var head := "[color=#%s]%s[/color]" % [faded(Color(e.color), age).to_html(false), e.head]
	if e.get("bracket", "") != "":
		head += " [color=#%s][lb]%s[rb][/color]" % [faded(Color(e.bracket_color), age).to_html(false), e.bracket]
	return "%s — %s" % [head, body]


## Characters an entry adds to the log's text (without the BBCode around them).
static func plain_length(e: Dictionary) -> int:
	var n: int = e.text.length()
	if e.head != "":
		n += e.head.length() + 3
		if e.get("bracket", "") != "":
			n += e.bracket.length() + 3
	return n


# ---------- the newest entry appears ----------

func _start_reveal(entry: Dictionary) -> void:
	_reveal_pos = -1.0
	if Settings.chars_per_second() <= 0.0:
		return
	_reveal_total = log_text.get_total_character_count()
	_reveal_pos = float(maxi(_reveal_total - plain_length(entry), 0))
	log_text.visible_characters = int(_reveal_pos)


## True while the newest entry is still appearing.
func revealing() -> bool:
	return _reveal_pos >= 0.0


## Shows the rest of the newest entry at once.
func finish_reveal() -> void:
	_reveal_pos = -1.0
	log_text.visible_characters = -1


func _process(delta: float) -> void:
	if panel.visible and Settings.pad_hints(pad_mode) != _hint_pad:
		_refresh_hint()
	if _reveal_pos < 0.0:
		return
	var cps := Settings.chars_per_second()
	_reveal_pos += cps * delta
	if cps <= 0.0 or _reveal_pos >= _reveal_total:
		finish_reveal()
	else:
		log_text.visible_characters = int(_reveal_pos)


# ---------- scrolling ----------

## Glides the log down to its end once the layout has settled (the responses below it change its height).
func _follow() -> void:
	if _following:
		return
	_following = true
	await get_tree().process_frame
	await get_tree().process_frame
	_following = false
	var bar := log_text.get_v_scroll_bar()
	var end := maxf(bar.max_value - bar.page, 0.0)
	if _scroll_tween:
		_scroll_tween.kill()
	if absf(bar.value - end) < 2.0:
		bar.value = end
		return
	_scroll_tween = create_tween()
	_scroll_tween.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	_scroll_tween.tween_property(bar, "value", end, SCROLL_S)


## True when the log shows its newest line.
func at_end() -> bool:
	var bar := log_text.get_v_scroll_bar()
	return bar.value >= bar.max_value - bar.page - 2.0


func _on_log_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		advance_requested.emit()


## Start a conversation: a fresh log and the speaker's portrait at the top of the column.
func begin_conversation(face: Texture2D) -> void:
	history.clear()
	log_text.text = ""
	finish_reveal()
	portrait.texture = face
	portrait.visible = face != null


func set_portrait(face: Texture2D) -> void:
	portrait.texture = face


## Numbered responses; on_choice gets the index of the one picked.
func set_options(labels: Array, on_choice: Callable) -> void:
	choices = labels
	_on_choice = on_choice
	_hot = (0 if choices.is_empty() else _step_from(-1, 1)) if pad_mode else -1
	_draw_option()
	_refresh_hint()
	_follow()


## The responses stay hidden while a speaker is still talking.
func set_options_visible(on: bool) -> void:
	option.visible = on
	_refresh_hint()
	_follow()


func is_locked(i: int) -> bool:
	return i >= 0 and i < choices.size() and choices[i] is Dictionary and choices[i].get("locked", false)


## The first response that is not locked going from `from` by `step`, wrapping; -1 when all are locked.
func _step_from(from: int, step: int) -> int:
	var n := choices.size()
	var i := from
	for _k in n:
		i = posmod(i + step, n)
		if not is_locked(i):
			return i
	return -1


## Controller: step the highlighted response (wraps, skips locked ones).
func move_option(step: int) -> void:
	if choices.is_empty() or suspended:
		return
	_hot = _step_from(_hot if _hot >= 0 else (-1 if step > 0 else choices.size()), step)
	_draw_option()


## Controller: pick the highlighted response.
func confirm_option() -> void:
	if option.visible:
		_pick(_hot if _hot >= 0 else _step_from(-1, 1))


func _draw_option() -> void:
	var labels: Array = choices if not choices.is_empty() else ["[Leave.]"]
	var rows: Array[String] = []
	for i in labels.size():
		var row := _option_bbcode(i, labels[i], i == _hot)
		rows.append(row if is_locked(i) else "[url=%d]%s[/url]" % [i, row])
	option.text = "\n".join(rows)


func _option_bbcode(i: int, c, hot: bool) -> String:
	var n := "%d. " % (i + 1)
	var lit := OPTION_HOT if hot else OPTION
	if c is String:
		return "[color=%s]%s%s[/color]" % [lit, n, c]
	var tag: String = _bold_chance(c.get("tag", ""))
	var tag_color: String = c.get("tag_color", WHITE_CHECK)
	if c.get("locked", false):
		var dim: String = LOCKED_RED if tag_color == RED_CHECK else LOCKED_WHITE
		return "[color=%s]%s[lb]%s[rb][/color] [color=%s][s]%s[/s][/color]" % [dim, n, tag, LOCKED_TEXT, c.text]
	var red := tag_color == RED_CHECK
	var text_color := (RED_TEXT_HOT if hot else RED_TEXT) if red else (WHITE_TEXT_HOT if hot else WHITE_TEXT)
	return "[color=%s]%s[lb]%s[rb][/color] [color=%s]%s[/color]" % [tag_color, n, tag, text_color, c.text]


## The chance in a check's tag in bold: "Bearing · Challenging 12 · [b]58%[/b]".
static func _bold_chance(tag: String) -> String:
	var end := tag.find("%")
	var start := end
	while start > 0 and tag[start - 1].is_valid_int():
		start -= 1
	if end < 0 or start == end:
		return tag
	return "%s[b]%s[/b]%s" % [tag.left(start), tag.substr(start, end - start + 1), tag.substr(end + 1)]


func _pick(i: int) -> void:
	if suspended:
		return
	_hot = -1
	if choices.is_empty() or not _on_choice.is_valid():
		close()
	elif i >= 0 and i < choices.size() and not is_locked(i):
		_on_choice.call(i)


func _unhandled_input(event: InputEvent) -> void:
	if panel.visible and option.visible and not suspended and event is InputEventKey and event.pressed:
		var i: int = event.keycode - KEY_1
		if i >= 0 and i < maxi(choices.size(), 1):
			_pick(i)
	if panel.visible and not suspended and event is InputEventKey and event.pressed:
		var bar := log_text.get_v_scroll_bar()
		match event.keycode:
			KEY_PAGEUP:
				bar.value -= bar.page * 0.8
			KEY_PAGEDOWN:
				bar.value += bar.page * 0.8


func is_open() -> bool:
	return panel.visible


func close() -> void:
	finish_reveal()
	if panel.visible:
		panel.visible = false
		portrait.visible = false
		option.visible = true
		_refresh_hint()
		choices = []
		_on_choice = Callable()
		closed.emit()


## Fade the screen to black (alpha 1) or back (0).
func fade_to(alpha: float, seconds: float) -> void:
	if seconds <= 0.0:
		fade.modulate.a = alpha
		return
	var tw := create_tween()
	tw.tween_property(fade, "modulate:a", alpha, seconds)
	await tw.finished


## Fade to black, show a title card, fade back. `midway` runs while the screen is black.
func title_card(text: String, midway: Callable = Callable()) -> void:
	busy = true
	hover.visible = false
	card.text = text
	var tw := create_tween()
	tw.tween_property(fade, "modulate:a", 1.0, 0.6)
	tw.tween_property(card, "modulate:a", 1.0, 0.4)
	tw.tween_interval(1.6)
	tw.tween_property(card, "modulate:a", 0.0, 0.4)
	if midway.is_valid():
		tw.tween_callback(midway)
	tw.tween_property(fade, "modulate:a", 0.0, 0.7)
	await tw.finished
	busy = false
