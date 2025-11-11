extends Camera2D


func _ready() -> void:
	add_to_group("camera")
	# Ensure camera can be shaken during pause
	process_mode = Node.PROCESS_MODE_ALWAYS
