extends Area3D

@export var quest_id: String = ""
@export var interaction_prompt: String = "Press 'E' to interact"

var player_in_range: bool = false
var game_state = GameState


func _ready():
	if quest_id.is_empty():
		push_warning("QuestTrigger: quest_id not set for %s" % name)


func _on_body_entered(body: Node3D):
	if body.name == "Player":  # Assuming player node is named "Player"
		player_in_range = true
		var can_start = QuestSystem.check_prerequisites(game_state.state, quest_id)
		if can_start:
			print("QuestTrigger: Player entered range (Ready)")
			# TODO: Show interaction_prompt in UI
		else:
			print("QuestTrigger: Player entered range (Locked)")


func _on_body_exited(body: Node3D):
	if body.name == "Player":
		print("QuestTrigger: Player exited range")
		player_in_range = false
		# TODO: Hide interaction_prompt in UI


func _input(event: InputEvent):
	if player_in_range and event.is_action_pressed("interact"):
		print("QuestTrigger: Interact pressed")
		if not quest_id.is_empty():
			if not QuestSystem.check_prerequisites(game_state.state, quest_id):
				print("QuestTrigger: Locked - Prerequisites not met")
				return

			# Start the quest
			game_state.dispatch(func(state): return QuestSystem.start_quest(state, quest_id))
			# For now, immediately complete it with a default approach for testing
			# In a real game, this would trigger dialogue or a more complex sequence
			game_state.dispatch(
				func(state): return QuestSystem.complete_quest(state, quest_id, "violent")
			)
			# Prevent multiple interactions
			queue_free()
