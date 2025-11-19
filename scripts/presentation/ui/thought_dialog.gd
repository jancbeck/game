extends Control

@onready var prompt_label: RichTextLabel = $Panel/PromptLabel
@onready var options_container: VBoxContainer = $Panel/OptionsContainer

var game_state = GameState
var current_thought_id: String = ""

func _ready():
	game_state.state_changed.connect(_on_state_changed)
	# Initial check
	_on_state_changed(game_state.state)

func _on_state_changed(state: Dictionary):
	if state.has("meta") and state["meta"].has("active_thought") and state["meta"]["active_thought"] != null:
		var thought_id = state["meta"]["active_thought"]
		if thought_id != current_thought_id:
			_show_thought(thought_id)
	else:
		if visible:
			_hide_thought()

func _show_thought(thought_id: String):
	current_thought_id = thought_id
	var data = DataLoader.get_thought(thought_id)
	if data.is_empty():
		return
		
	visible = true
	prompt_label.text = data["prompt"]
	
	# Clear existing buttons
	for child in options_container.get_children():
		child.queue_free()
		
	# Create new buttons
	for i in range(data["options"].size()):
		var option = data["options"][i]
		var btn = Button.new()
		btn.text = option["text"]
		btn.pressed.connect(_on_option_selected.bind(i))
		options_container.add_child(btn)
	
	# Pause game
	get_tree().paused = true

func _hide_thought():
	visible = false
	current_thought_id = ""
	get_tree().paused = false

func _on_option_selected(index: int):
	game_state.dispatch(func(state): return ThoughtSystem.choose_thought(state, index))
