extends Area3D

## Persistent NPC entity that triggers Dialogic conversations.
## Unlike QuestTrigger, NPCs persist after interaction and use dynamic timelines.

@export var npc_id: String = ""
@export var interaction_prompt: String = "Press 'E' to talk"

var player_in_range: bool = false
var game_state = GameState
var _timeline_started: bool = false  # Prevents duplicate timeline starts


func _ready():
	if npc_id.is_empty():
		push_warning("NPCEntity: npc_id not set for %s" % name)
		return

	# Log NPC initialization
	if LogSystem:
		LogSystem.add_log_entry(
			LogSystem.Level.DEBUG,
			LogSystem.Category.QUEST,
			"npc_entity_initialized",
			{"npc_id": npc_id, "position": global_position}
		)

	# Check if NPC should spawn (is alive)
	if not _should_spawn():
		if LogSystem:
			LogSystem.add_log_entry(
				LogSystem.Level.DEBUG,
				LogSystem.Category.QUEST,
				"npc_entity_despawned",
				{"npc_id": npc_id, "reason": "npc_not_alive"}
			)
		queue_free()
		return

	# Listen for state changes to despawn if NPC dies
	if game_state.state_changed.connect(_on_state_changed) != OK:
		push_warning("NPCEntity: Failed to connect to state_changed signal")

	# Update label with NPC name
	var label = get_node_or_null("Label3D")
	if label:
		label.text = _get_npc_display_name()


func _on_state_changed(_new_state: Dictionary) -> void:
	# Despawn if NPC is no longer alive
	if not _should_spawn():
		if LogSystem:
			LogSystem.add_log_entry(
				LogSystem.Level.INFO,
				LogSystem.Category.QUEST,
				"npc_entity_despawned",
				{"npc_id": npc_id, "reason": "npc_died"}
			)
		queue_free()


func _should_spawn() -> bool:
	"""Check if NPC should exist in world (is alive)."""
	# For now, all NPCs exist by default
	# TODO: Check state["world"]["npc_states"][npc_id]["alive"] when NPC data exists
	return true


func _get_npc_display_name() -> String:
	"""Get display name for NPC label."""
	# TODO: Load from NPC data file when available
	# For now, convert npc_id to title case
	return npc_id.capitalize()


func _on_body_entered(body: Node3D):
	if body.name == "Player":
		player_in_range = true
		_timeline_started = false  # Reset flag when player enters range
		if LogSystem:
			LogSystem.add_log_entry(
				LogSystem.Level.DEBUG,
				LogSystem.Category.QUEST,
				"npc_interaction_available",
				{"npc_id": npc_id}
			)
		# TODO: Show interaction_prompt in UI


func _on_body_exited(body: Node3D):
	if body.name == "Player":
		player_in_range = false
		# TODO: Hide interaction_prompt in UI


func _input(event: InputEvent):
	if player_in_range and event.is_action_pressed("interact"):
		if npc_id.is_empty():
			return

		# Debounce: prevent starting same timeline multiple times
		if _timeline_started:
			return
		_timeline_started = true

		# Get dynamic timeline based on NPC state and relationship
		var timeline_id = _get_conversation_timeline()

		if timeline_id.is_empty():
			push_warning("NPCEntity: No timeline found for NPC '%s'" % npc_id)
			_timeline_started = false
			return

		if LogSystem:
			LogSystem.add_log_entry(
				LogSystem.Level.INFO,
				LogSystem.Category.QUEST,
				"npc_conversation_started",
				{"npc_id": npc_id, "timeline_id": timeline_id}
			)

		# Access DialogSystem (must be in scene tree or as autoload)
		var dialog_system = get_node_or_null("/root/DialogSystem")
		if dialog_system and dialog_system.has_method("start_timeline"):
			dialog_system.start_timeline(timeline_id)
		else:
			push_error("DialogSystem not found. Add it as autoload or to scene.")
			_timeline_started = false


func _get_conversation_timeline() -> String:
	"""Determine which timeline to play based on NPC state and relationship.

	Priority:
	1. Quest-specific timeline (if active quest involves NPC)
	2. Relationship-based timeline (based on relationship level)
	3. Default greeting timeline

	Returns timeline ID string or empty string if none found.
	"""
	# For now, use simple pattern: npc_{npc_id}_greeting
	# TODO: Implement relationship-based timeline selection when NPC data exists
	var base_timeline = "npc_%s_greeting" % npc_id

	# Check if timeline exists (will implement proper check later)
	# For now, return the base timeline
	return base_timeline
