extends Control
## Dialogue panel: speaker name, text, and option buttons.
## Locked options (Disco Elysium-style) render greyed and unclickable.

signal option_chosen(option_index: int)

@onready var speaker_label: Label = %SpeakerLabel
@onready var text_label: RichTextLabel = %TextLabel
@onready var options_box: VBoxContainer = %OptionsBox
@onready var portrait_rect: TextureRect = %PortraitRect

var _click_player: AudioStreamPlayer


func _ready() -> void:
	hide()
	_click_player = AudioStreamPlayer.new()
	if ResourceLoader.exists("res://art/audio/ui_click.wav"):
		_click_player.stream = load("res://art/audio/ui_click.wav")
	add_child(_click_player)


func show_node(
	speaker: String, text: String, options: Array[Dictionary], portrait: Texture2D = null
) -> void:
	speaker_label.text = speaker
	text_label.text = text
	portrait_rect.texture = portrait
	portrait_rect.visible = portrait != null
	for child in options_box.get_children():
		child.queue_free()
	for option in options:
		var button := Button.new()
		button.text = option["text"]
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		if option["available"]:
			var idx: int = option["index"]
			button.pressed.connect(
				func() -> void:
					_click_player.play()
					option_chosen.emit(idx)
			)
		else:
			button.disabled = true
			button.text += "  [locked]"
		options_box.add_child(button)
	show()
