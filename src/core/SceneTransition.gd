extends CanvasLayer

var is_transitioning := false


func _ready() -> void:
	if not has_node("ColorRect"):
		push_error("SceneTransition: ColorRect node not found!")
		return
	$"ColorRect".modulate = Color(0, 0, 0, 0)
	layer = 100  # Above all gameplay elements


func fade_to_black_and_reload(duration: float = 0.8) -> void:
	if not has_node("ColorRect"):
		push_error("SceneTransition: ColorRect not found, can't fade")
		get_tree().reload_current_scene()
		return

	if is_transitioning:
		return
	is_transitioning = true

	$"ColorRect".visible = true

	# Freeze player and enemies during transition
	_freeze_gameplay()

	# Fade out to black
	var tween := create_tween()
	tween.tween_property($"ColorRect", "modulate:a", 1.0, duration).from(0.0)
	tween.set_ease(Tween.EASE_IN_OUT)
	tween.set_trans(Tween.TRANS_CUBIC)
	await tween.finished

	# Hold on black screen before reloading
	await get_tree().create_timer(0.5).timeout

	get_tree().reload_current_scene()

	# Wait for scene to fully initialize before fading back in
	await get_tree().process_frame
	await get_tree().process_frame

	# Reset music to calm (non-aggro)
	MusicManager.stop_all()
	MusicManager.start_room_music()

	# Fade in from black
	var tween_in := create_tween()
	tween_in.tween_property($"ColorRect", "modulate:a", 0.0, duration).from(1.0)
	tween_in.set_ease(Tween.EASE_IN_OUT)
	tween_in.set_trans(Tween.TRANS_CUBIC)
	await tween_in.finished

	is_transitioning = false


func fade_to_black_on_death(duration: float = 0.8) -> void:
	if not has_node("ColorRect"):
		push_error("SceneTransition: ColorRect not found, can't fade")
		get_tree().reload_current_scene()
		return

	if is_transitioning:
		return
	is_transitioning = true

	$"ColorRect".visible = true

	# Freeze player and enemies during transition
	_freeze_gameplay()

	# Move player to a higher canvas layer so it stays visible
	var player := get_tree().get_first_node_in_group("player")
	var player_original_parent: Node = null
	var player_canvas_layer: CanvasLayer = null

	if player:
		player_original_parent = player.get_parent()
		player_canvas_layer = CanvasLayer.new()
		player_canvas_layer.layer = 101  # Above the fade overlay at layer 100
		get_tree().current_scene.add_child(player_canvas_layer)
		player.reparent(player_canvas_layer)

	# Fade out to black (everything except player)
	var tween := create_tween()
	tween.tween_property($"ColorRect", "modulate:a", 1.0, duration).from(0.0)
	tween.set_ease(Tween.EASE_IN_OUT)
	tween.set_trans(Tween.TRANS_CUBIC)
	await tween.finished

	# Hold on black screen before reloading
	await get_tree().create_timer(0.5).timeout

	get_tree().reload_current_scene()

	# Wait for scene to fully initialize before fading back in
	await get_tree().process_frame
	await get_tree().process_frame

	# Reset music to calm (non-aggro)
	MusicManager.stop_all()
	MusicManager.start_room_music()

	# Fade in from black
	var tween_in := create_tween()
	tween_in.tween_property($"ColorRect", "modulate:a", 0.0, duration).from(1.0)
	tween_in.set_ease(Tween.EASE_IN_OUT)
	tween_in.set_trans(Tween.TRANS_CUBIC)
	await tween_in.finished

	is_transitioning = false


func _freeze_gameplay() -> void:
	# Disable physics processing for player and enemies
	var player := get_tree().get_first_node_in_group("player")
	if player:
		player.set_physics_process(false)

	for enemy in get_tree().get_nodes_in_group("enemies"):
		enemy.set_physics_process(false)
