extends Area3D

const DataLoader = preload("res://scripts/data/data_loader.gd")
const DialogicResourceUtil = preload("res://addons/dialogic/Core/DialogicResourceUtil.gd")

@export var quest_id: String = ""
@export var interaction_prompt: String = "Press 'E' to interact"
@export var timeline_id: String = ""  ## Dialogic timeline to start on interaction

## Debug-only: Auto-complete quest with this approach when interacting (bypasses Dialogic)
@export var debug_auto_complete_approach: String = ""

var player_in_range: bool = false
var game_state = GameState
var _timeline_started: bool = false  # Prevents duplicate timeline starts


func _ready():
	if quest_id.is_empty():
		push_warning("QuestTrigger: quest_id not set for %s" % name)

	# Log trigger initialization
	if LogSystem:
		LogSystem.add_log_entry(
			LogSystem.Level.DEBUG,
			LogSystem.Category.QUEST,
			"quest_trigger_initialized",
			{"quest_id": quest_id, "position": global_position, "timeline_id": timeline_id}
		)

	# Check initial state and remove if quest is already completed
	_check_and_remove_if_completed()

	# Listen for state changes to remove trigger when quest is completed
	if game_state.state_changed.connect(_on_state_changed) != OK:
		push_warning("QuestTrigger: Failed to connect to state_changed signal")


func _on_state_changed(_new_state: Dictionary) -> void:
	_check_and_remove_if_completed()


func _check_and_remove_if_completed() -> void:
	# Remove trigger if quest is completed (NOT if just active)
	if game_state.state.has("quests") and game_state.state["quests"].has(quest_id):
		var status = game_state.state["quests"][quest_id]["status"]
		if status == "completed":  # Changed from != "available" to fix trigger disappearing
			if LogSystem:
				LogSystem.add_log_entry(
					LogSystem.Level.DEBUG,
					LogSystem.Category.QUEST,
					"quest_trigger_removed",
					{"quest_id": quest_id, "reason": "quest_completed"}
				)
			queue_free()


func _on_body_entered(body: Node3D):
	if body.name == "Player":  # Assuming player node is named "Player"
		player_in_range = true
		_timeline_started = false  # Reset flag when player enters range
		var can_start = QuestSystem.check_prerequisites(game_state.state, quest_id)
		if can_start:
			if LogSystem:
				LogSystem.add_log_entry(
					LogSystem.Level.DEBUG,
					LogSystem.Category.QUEST,
					"quest_trigger_in_range",
					{"quest_id": quest_id, "locked": false}
				)
			# TODO: Show interaction_prompt in UI
		else:
			if LogSystem:
				LogSystem.add_log_entry(
					LogSystem.Level.DEBUG,
					LogSystem.Category.QUEST,
					"quest_trigger_in_range",
					{"quest_id": quest_id, "locked": true}
				)


func _on_body_exited(body: Node3D):
	if body.name == "Player":
		player_in_range = false
		# TODO: Hide interaction_prompt in UI


func _input(event: InputEvent):
	if player_in_range and event.is_action_pressed("interact"):
		if not quest_id.is_empty():
			# Debug mode: Auto-complete quest immediately
			if not debug_auto_complete_approach.is_empty():
				if LogSystem:
					LogSystem.add_log_entry(
						LogSystem.Level.DEBUG,
						LogSystem.Category.QUEST,
						"quest_auto_completed_debug",
						{"quest_id": quest_id, "approach": debug_auto_complete_approach}
					)
				game_state.dispatch(func(state): return QuestSystem.start_quest(state, quest_id))
				game_state.dispatch(
					func(state):
						return QuestSystem.complete_quest(
							state, quest_id, debug_auto_complete_approach
						)
				)
				return

			# New behavior: Start Dialogic timeline if configured
			# QuestTrigger enforces prerequisites; timeline assumes quest is startable
			if not timeline_id.is_empty():
				# Debounce: prevent starting same timeline multiple times
				if _timeline_started:
					return
				_timeline_started = true

				# Get quest status to determine which timeline to use
				var quest_status := _get_quest_status()

				# Completed quests: don't re-trigger
				if quest_status == "completed":
					_timeline_started = false
					return

				# Active quests: try resolution timeline, fallback to base timeline
				var selected_timeline := _get_timeline_for_quest_status(quest_status)

				# Available quests: Check prerequisites BEFORE starting timeline
				if quest_status == "available":
					if not QuestSystem.can_start_quest(game_state.state, quest_id):
						if LogSystem:
							LogSystem.add_log_entry(
								LogSystem.Level.WARN,
								LogSystem.Category.QUEST,
								"quest_locked",
								{"quest_id": quest_id, "reason": "prerequisites_not_met"}
							)
						_timeline_started = false
						return

				if LogSystem:
					LogSystem.add_log_entry(
						LogSystem.Level.INFO,
						LogSystem.Category.QUEST,
						"quest_timeline_started",
						{"quest_id": quest_id, "timeline_id": selected_timeline}
					)
				# Access DialogSystem (must be in scene tree or as autoload)
				var dialog_system = get_node_or_null("/root/DialogSystem")
				if dialog_system and dialog_system.has_method("start_timeline"):
					dialog_system.start_timeline(selected_timeline)
				else:
					push_error("DialogSystem not found. Add it as autoload or to scene.")
				return

			# Fallback: Old behavior (direct quest start)
			# This path is deprecated and will be removed after migration
			# Only check prerequisites for the fallback path
			if not QuestSystem.check_prerequisites(game_state.state, quest_id):
				return

			game_state.dispatch(func(state): return QuestSystem.start_quest(state, quest_id))


func _get_quest_status() -> String:
	"""Returns current quest status from GameState. Returns 'available' if quest not found."""
	if game_state.state.has("quests") and game_state.state["quests"].has(quest_id):
		return game_state.state["quests"][quest_id]["status"]
	return "available"


func _get_timeline_for_quest_status(quest_status: String) -> String:
	"""Selects appropriate timeline based on quest status.
	- 'available' → use base timeline_id
	- 'active' → try replacing '_intro' with '_resolution', fallback to base
	- 'completed' → should not be called (handled earlier)
	Returns timeline identifier string."""

	# Base case: use configured timeline_id
	if quest_status == "available":
		print("QuestTrigger: Using base timeline '%s' for available quest" % timeline_id)
		return timeline_id

	# Active quest: try resolution variant
	if quest_status == "active":
		# Resolution timeline naming: replace '_intro' with '_resolution'
		# Example: 'quest_investigate_ruins_intro' → 'quest_investigate_ruins_resolution'
		var resolution_timeline := timeline_id.replace("_intro", "_resolution")

		# Check if resolution timeline exists using Dialogic API
		if DialogicResourceUtil.timeline_resource_exists(resolution_timeline):
			print(
				(
					"QuestTrigger: Using resolution timeline '%s' for active quest"
					% resolution_timeline
				)
			)
			return resolution_timeline

		push_warning(
			(
				"QuestTrigger: Resolution timeline '%s' not found, falling back to base timeline '%s'"
				% [resolution_timeline, timeline_id]
			)
		)
		return timeline_id

	# Fallback for any unknown status
	push_warning("QuestTrigger: Unexpected quest status '%s', using base timeline" % quest_status)
	return timeline_id
