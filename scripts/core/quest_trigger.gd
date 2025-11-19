extends Area3D

@export var quest_id: String = ""
@export var interaction_prompt: String = "Press 'E' to interact"
@export var timeline_id: String = ""  ## Dialogic timeline to start on interaction


var player_in_range: bool = false
var game_state = GameState


func _ready():
	if quest_id.is_empty():
		push_warning("QuestTrigger: quest_id not set for %s" % name)
	
	# Check initial state and remove if quest is already active/completed
	_check_and_remove_if_completed()
	
	# Listen for state changes to remove trigger when quest is completed
	if game_state.state_changed.connect(_on_state_changed) != OK:
		push_warning("QuestTrigger: Failed to connect to state_changed signal")


func _on_state_changed(_new_state: Dictionary) -> void:
	_check_and_remove_if_completed()


func _check_and_remove_if_completed() -> void:
	# Remove trigger if quest is already active or completed
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
			# New behavior: Start Dialogic timeline if configured
			# The timeline itself handles prerequisite checks and messages
			if not timeline_id.is_empty():
				print("QuestTrigger: Starting Dialogic timeline '%s'" % timeline_id)
				# Access DialogSystem (must be in scene tree or as autoload)
				var dialog_system = get_node_or_null("/root/DialogSystem")
				if dialog_system and dialog_system.has_method("start_timeline"):
					dialog_system.start_timeline(timeline_id)
				else:
					push_error("DialogSystem not found. Add it as autoload or to scene.")
				return
			
			# Fallback: Old behavior (direct quest start)
			# This path is deprecated and will be removed after migration
			# Only check prerequisites for the fallback path
			if not QuestSystem.check_prerequisites(game_state.state, quest_id):
				print("QuestTrigger: Locked - Prerequisites not met")
				return
			
			game_state.dispatch(func(state): return QuestSystem.start_quest(state, quest_id))
			print("Quest started via legacy fallback.")
