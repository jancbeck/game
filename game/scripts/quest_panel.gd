## F1: the quest state. Where the figure is, what it carries, the skill values, and every story
## variable and quest flag with its value (the same store main.quest reads and the save keeps).
extends CanvasLayer

var main
var label: Label
var _since := 1.0


func setup(m) -> void:
	main = m
	layer = 8
	var panel := PanelContainer.new()
	panel.position = Vector2(30, 30)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.02, 0.02, 0.025, 0.82)
	sb.set_content_margin_all(16)
	panel.add_theme_stylebox_override("panel", sb)
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(panel)
	label = Label.new()
	var font := SystemFont.new()
	font.font_names = PackedStringArray(["Menlo", "Monaco", "monospace"])
	label.add_theme_font_override("font", font)
	label.add_theme_font_size_override("font_size", 22)
	label.add_theme_color_override("font_color", Color(0.86, 0.83, 0.76))
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(label)
	visibility_changed.connect(func():
		if visible:
			label.text = describe()
			_since = 0.0)
	hide()


func _process(delta: float) -> void:
	if not visible:
		return
	_since += delta
	if _since >= 0.25:
		_since = 0.0
		label.text = describe()
		label.get_parent().reset_size()


func describe() -> String:
	var s = main.session
	var carried: Array = s.inventory.list().map(func(id): return "%s%s" % [s.inventory.item_name(id),
			" x%d" % s.inventory.count(id) if s.inventory.count(id) > 1 else ""])
	var lines: Array[String] = ["QUEST STATE",
		"location  %s  (been to: %s)" % [s.location, ", ".join(s.visited.keys())],
		"carrying  %s" % (", ".join(carried) if not carried.is_empty() else "nothing"),
		"skills    %s" % ", ".join(s.skills.ids().map(func(id): return "%s %d" % [id, s.skills.value(id)]))]
	var vars: Dictionary = s.quest.all()
	for k in vars:
		lines.append("  %s = %s" % [k, var_to_str(vars[k]) if vars[k] is Array or vars[k] is Dictionary else str(vars[k])])
	return "\n".join(lines)
