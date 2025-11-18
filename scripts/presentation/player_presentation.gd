extends CharacterBody3D

func _ready():
	GameState.state_changed.connect(_on_state_changed)
	# Initialize with current state
	_on_state_changed(GameState.state)

func _on_state_changed(state: Dictionary):
	# Update presentation from state
	global_position = state["player"]["position"]

func _physics_process(delta):
	# Read input
	var input_dir = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	
	if input_dir != Vector2.ZERO:
		# Dispatch action
		var direction = Vector3(input_dir.x, 0, input_dir.y)
		
		# Use a lambda to bind arguments if needed, or just call the static function inside the lambda
		GameState.dispatch(func(s): return PlayerSystem.move(s, direction, delta))
