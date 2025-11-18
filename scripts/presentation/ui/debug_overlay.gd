extends CanvasLayer

@onready var label: RichTextLabel = $RichTextLabel


func _ready():
	GameState.state_changed.connect(_on_state_changed)
	_on_state_changed(GameState.state)


func _on_state_changed(state: Dictionary):
	var flexibility_str = JSON.stringify(state["player"]["flexibility"], "\t", true)
	var convictions_str = JSON.stringify(state["player"]["convictions"], "\t", true)
	label.set_text("Flexibility:\n" + flexibility_str + "\n\nConvictions:\n" + convictions_str)
