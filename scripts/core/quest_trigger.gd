extends Area3D

@export var quest_id: String = ""
@export var interaction_prompt: String = "Press 'E' to interact"
## If set, immediately completes the quest with this approach upon interaction (for testing).
@export var debug_auto_complete_approach: String = ""

var player_in_range: bool = false
var game_state = GameState


func _ready():
	if quest_id.is_empty():
		push_warning("QuestTrigger: quest_id not set for %s" % name)
	
	# Check if quest is already active or completed in state, and remove trigger if so.
	# This ensures triggers don't reappear after loading a save where they were finished.
	if game_state.state.has("quests") and game_state.state["quests"].has(quest_id):
		var status = game_state.state["quests"][quest_id]["status"]
		if status != "available":
			queue_free()


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
			
			if not debug_auto_complete_approach.is_empty():
				game_state.dispatch(
					func(state): return QuestSystem.complete_quest(state, quest_id, debug_auto_complete_approach)
				)
				# Check for thought trigger
				var trigger_string = "quest_complete:%s:%s" % [quest_id, debug_auto_complete_approach]
				var thought_id = ThoughtSystem.get_thought_for_trigger(trigger_string)
				if not thought_id.is_empty():
					game_state.dispatch(func(state): return ThoughtSystem.present_thought(state, thought_id))
				
				# Prevent multiple interactions only if completed
				queue_free()
			else:
				print("Quest started. No auto-complete approach set.")
