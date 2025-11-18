extends CharacterBody3D

@onready var mesh: MeshInstance3D = $"MeshInstance3D"
var game_state = GameState


func _ready():
	game_state.state_changed.connect(_on_state_changed)
	# Initialize with current state
	call_deferred("_on_state_changed", game_state.state)


func _on_state_changed(state: Dictionary):
	# Update presentation from state
	global_position = state["player"]["position"]

	# Visual feedback for degradation (color shift)
	if mesh:
		var flexibility_stats = state["player"]["flexibility"]
		var avg_flexibility = (
			(flexibility_stats.charisma + flexibility_stats.cunning + flexibility_stats.empathy)
			/ 3.0
		)

		var material: StandardMaterial3D = (
			mesh.get_surface_override_material(0) as StandardMaterial3D
		)
		
		if not material:
			material = StandardMaterial3D.new()
			mesh.set_surface_override_material(0, material)
			
		if material:
			var r = 1.0 - (avg_flexibility / 10.0)
			var g = avg_flexibility / 10.0
			material.albedo_color = Color(r, g, 0.0)


func _physics_process(delta):
	# Read input
	var input_dir = Input.get_vector("move_left", "move_right", "move_forward", "move_back")

	if input_dir != Vector2.ZERO:
		# Dispatch action
		var direction = Vector3(input_dir.x, 0, input_dir.y)

		# Use a lambda to bind arguments if needed, or just call the static function inside the lambda
		game_state.dispatch(func(s): return PlayerSystem.move(s, direction, delta))
