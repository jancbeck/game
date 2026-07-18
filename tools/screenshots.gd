extends SceneTree
## Renders review screenshots of the real game. Needs an actual renderer,
## so CI runs it under xvfb with Mesa/llvmpipe (NOT --headless):
##   xvfb-run -a godot --rendering-driver opengl3 -s tools/screenshots.gd
## Writes PNGs to res://screenshots/ for the CI job to publish.

const OUT_DIR := "res://screenshots"

var shots := 0


func _initialize() -> void:
	# Failsafe so a script error can't hang CI until the job timeout.
	create_timer(120.0).timeout.connect(
		func() -> void:
			printerr("screenshots timed out")
			quit(1)
	)
	call_deferred("_run")


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	var packed: PackedScene = load("res://scenes/main.tscn")
	var main: Node = packed.instantiate()
	root.add_child(main)
	# Let the camera rig settle and lights/shadows warm up.
	for i in 60:
		await process_frame
	await _snap("01_world")

	# Walk forward a bit so the pose reads as "in motion".
	Input.action_press("move_up")
	for i in 30:
		await process_frame
	Input.action_release("move_up")
	await _snap("02_walking")

	# Open the gatekeeper conversation through the real UI path.
	main.start_dialogue(main.get_node("Gatekeeper"))
	for i in 10:
		await process_frame
	await _snap("03_dialogue")

	# Drive the conversation to completion so a quest is completed, another
	# starts, and a journal entry is recorded — then open the narrative HUD.
	_choose(main, "brandy")
	_choose(main, "[Enter the camp]")
	main.toggle_journal()
	for i in 10:
		await process_frame
	await _snap("07_journal")
	main.toggle_journal()

	# The painted scene (Disco Elysium-style pipeline).
	main.queue_free()
	await process_frame
	var painted: Node = (load("res://scenes/painted/prison_yard.tscn") as PackedScene).instantiate()
	root.add_child(painted)
	for i in 30:
		await process_frame
	await _snap("04_prison_yard")
	painted.start_dialogue(painted.npcs[0])
	for i in 10:
		await process_frame
	await _snap("05_prison_dialogue")
	painted._on_dialogue_ended()
	# Occlusion proof: stand in the pocket behind the gallows platform —
	# the character must be partially hidden by the painted foreground.
	painted.player.position = painted.px_to_world(Vector2(1100, 560))
	for i in 5:
		await process_frame
	await _snap("06_occlusion")

	# Cutscene set-piece: kick off the scripted escort and capture it mid-play —
	# a narration line on screen, actors repositioned by the timeline, no HUD
	# prompt (player input is suspended). Not awaited: the coroutine resumes on
	# process frames while we let it run into a walk, then snap.
	painted.play_cutscene("escort_departure")
	for i in 70:
		await process_frame
	await _snap("08_cutscene")
	print("Screenshots written: %d" % shots)
	quit(0 if shots == 8 else 1)


## Pick the first available dialogue option whose text contains `substring`.
func _choose(main: Node, substring: String) -> void:
	if main.runner == null:
		return
	var store: Node = root.get_node("/root/Store")
	var options: Array[Dictionary] = main.runner.visible_options(store.get_state())
	for option in options:
		if option["available"] and substring in str(option["text"]):
			main._on_option_chosen(option["index"])
			return


func _snap(shot_name: String) -> void:
	await RenderingServer.frame_post_draw
	var img: Image = root.get_texture().get_image()
	var path := "%s/%s.png" % [OUT_DIR, shot_name]
	var err := img.save_png(ProjectSettings.globalize_path(path))
	if err == OK:
		shots += 1
		print("saved %s" % path)
	else:
		printerr("FAILED to save %s (%d)" % [path, err])
