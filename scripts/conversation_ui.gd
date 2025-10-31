extends CanvasLayer

@onready var speaker_label : Label = $Panel/VBox/Speaker
@onready var line_label : RichTextLabel = $Panel/VBox/Line
@onready var options_container : VBoxContainer = $Panel/VBox/Options
@onready var continue_button : Button = $Panel/ContinueButton

var manager : Node

func set_manager(new_manager : Node) -> void:
    manager = new_manager
    continue_button.pressed.connect(manager._on_continue_pressed)

func show_line(data : Dictionary) -> void:
    visible = true
    speaker_label.text = data.get("speaker", "")
    line_label.text = data.get("text", "")
    _populate_options(data.get("options", []))
    var show_continue := data.get("auto_continue", false)
    continue_button.visible = show_continue

func hide_ui() -> void:
    visible = false
    for child in options_container.get_children():
        child.queue_free()
    continue_button.visible = false

func _populate_options(options : Array) -> void:
    for child in options_container.get_children():
        child.queue_free()
    if options.is_empty():
        return
    for option in options:
        var button := Button.new()
        button.text = option.get("text", "...")
        button.disabled = option.get("disabled", false)
        button.pressed.connect(_on_option_pressed.bind(option))
        options_container.add_child(button)

func _on_option_pressed(option : Dictionary) -> void:
    if manager:
        manager._on_option_selected(option)
