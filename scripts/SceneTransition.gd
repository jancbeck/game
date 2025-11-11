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

	# Fade in from black
	var tween_in := create_tween()
	tween_in.tween_property($"ColorRect", "modulate:a", 0.0, duration).from(1.0)
	tween_in.set_ease(Tween.EASE_IN_OUT)
	tween_in.set_trans(Tween.TRANS_CUBIC)
	await tween_in.finished

	is_transitioning = false
