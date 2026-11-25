## The satchel: a strip of slots at the bottom of the screen in the dialogue column's style (dark
## panel, brass rule, serif), the name and description of the highlighted item beneath it, and a
## short notice when something is taken or given away. I or the pad's Y / Menu toggles it.
extends CanvasLayer

const INK := Color(0.86, 0.83, 0.76)
const BRASS := Color(0.55, 0.45, 0.3)
const GOLD := Color("#d9b77a")
const SLOT := 92

var main
var inv
var font: SystemFont
var panel: PanelContainer
var row: HBoxContainer
var name_label: Label
var desc_label: Label
var notice: Label
var selected := 0
var _slots: Array[PanelContainer] = []
var _notice_tween: Tween

func setup(m, inventory, ui_font: SystemFont) -> void:
	main = m
	inv = inventory
	font = ui_font
	layer = 9
	panel = PanelContainer.new()
	panel.anchor_left = 0.5
	panel.anchor_right = 0.5
	panel.anchor_top = 1.0
	panel.anchor_bottom = 1.0
	panel.grow_horizontal = Control.GROW_DIRECTION_BOTH
	panel.grow_vertical = Control.GROW_DIRECTION_BEGIN
	panel.offset_bottom = -40
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.035, 0.035, 0.04, 0.9)
	sb.border_color = Color(BRASS, 0.5)
	sb.border_width_top = 2
	sb.content_margin_left = 30
	sb.content_margin_right = 30
	sb.content_margin_top = 20
	sb.content_margin_bottom = 22
	panel.add_theme_stylebox_override("panel", sb)
	panel.visible = false
	add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	panel.add_child(box)
	var title := _label(22, GOLD)
	title.text = "SATCHEL"
	box.add_child(title)
	row = HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	box.add_child(row)
	name_label = _label(28, GOLD)
	box.add_child(name_label)
	desc_label = _label(24, INK)
	desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc_label.custom_minimum_size = Vector2(900, 0)
	box.add_child(desc_label)

	notice = _label(30, INK)
	notice.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	notice.add_theme_constant_override("outline_size", 8)
	notice.set_anchors_preset(Control.PRESET_TOP_WIDE)
	notice.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	notice.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	notice.offset_top = 70
	notice.offset_left = 40
	notice.offset_right = -40
	notice.modulate.a = 0.0
	add_child(notice)
	inv.changed.connect(func(_id, _d): _rebuild())


func _label(size: int, color: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_override("font", font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func is_open() -> bool:
	return panel != null and panel.visible


func toggle() -> void:
	if is_open():
		close()
	else:
		open()


func open() -> void:
	selected = clampi(selected, 0, maxi(inv.list().size() - 1, 0))
	_rebuild()
	panel.visible = true


func close() -> void:
	panel.visible = false


func move(step: int) -> void:
	var n: int = inv.list().size()
	if n > 0:
		selected = posmod(selected + step, n)
		_rebuild()


func _rebuild() -> void:
	var ids: Array = inv.list()
	selected = clampi(selected, 0, maxi(ids.size() - 1, 0))
	for s in _slots:
		s.queue_free()
	_slots.clear()
	for i in ids.size():
		var slot := _slot(ids[i], i == selected)
		slot.mouse_filter = Control.MOUSE_FILTER_STOP
		slot.mouse_entered.connect(func():
			selected = i
			_rebuild())
		row.add_child(slot)
		_slots.append(slot)
	if ids.is_empty():
		name_label.text = ""
		desc_label.text = "Nothing in the satchel."
	else:
		var d: Dictionary = inv.defs[ids[selected]]
		name_label.text = d.name
		desc_label.text = d.get("description", "")


func _slot(id: String, hot: bool) -> PanelContainer:
	var p := PanelContainer.new()
	p.custom_minimum_size = Vector2(SLOT, SLOT)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.09, 0.085, 0.08, 0.95)
	sb.border_color = GOLD if hot else Color(BRASS, 0.5)
	sb.set_border_width_all(3 if hot else 1)
	sb.set_corner_radius_all(3)
	p.add_theme_stylebox_override("panel", sb)
	var d: Dictionary = inv.defs[id]
	var icon_path: String = d.get("icon", "")
	if icon_path != "" and FileAccess.file_exists("res://" + icon_path):
		var t := TextureRect.new()
		t.texture = ImageTexture.create_from_image(Image.load_from_file(ProjectSettings.globalize_path("res://" + icon_path)))
		t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		t.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		t.mouse_filter = Control.MOUSE_FILTER_IGNORE
		p.add_child(t)
	else:
		# no picture: the item's initial, like an illuminated capital
		var l := _label(52, Color(GOLD, 0.9 if hot else 0.6))
		l.text = String(d.name).left(1).to_upper()
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		p.add_child(l)
	if inv.count(id) > 1:
		var n := _label(22, INK)
		n.text = str(inv.count(id))
		n.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		n.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
		p.add_child(n)
	return p


## The notice stays left of the dialogue column while that is open.
func _process(_delta: float) -> void:
	if notice.modulate.a > 0.01:
		var right: int = main.ui.COLUMN_W + 2 * main.ui.COLUMN_EDGE if main.ui.is_open() else 40
		notice.offset_right = -right


## A line near the top of the screen that fades out, e.g. "Taken: Gate key".
func toast(text: String) -> void:
	notice.text = text
	if _notice_tween:
		_notice_tween.kill()
	_notice_tween = create_tween()
	_notice_tween.tween_property(notice, "modulate:a", 1.0, 0.2)
	_notice_tween.tween_interval(2.2)
	_notice_tween.tween_property(notice, "modulate:a", 0.0, 0.7)
