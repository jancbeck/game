extends Control
## Dialogue panel: speaker name, text, and option buttons.
## Locked options (Disco Elysium-style) render greyed and unclickable.

signal option_chosen(option_index: int)

@onready var speaker_label: Label = %SpeakerLabel
@onready var text_label: RichTextLabel = %TextLabel
@onready var options_box: VBoxContainer = %OptionsBox


func _ready() -> void:
	hide()


func show_node(speaker: String, text: String, options: Array[Dictionary]) -> void:
	speaker_label.text = speaker
	text_label.text = text
	for child in options_box.get_children():
		child.queue_free()
	for option in options:
		var button := Button.new()
		button.text = option["text"]
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		if option["available"]:
			var idx: int = option["index"]
			button.pressed.connect(func() -> void: option_chosen.emit(idx))
		else:
			button.disabled = true
			button.text += "  [locked]"
		options_box.add_child(button)
	show()
