extends SceneTree
## Headless smoke test — the CI ground truth that the GAME (not just the
## logic) boots and plays. Run with:
##   godot --headless -s tools/smoke_test.gd
## Loads the real main scene with real autoloads, drives a full in-scene
## dialogue playthrough through main.gd's own code path, saves, loads,
## and exits 0 only if every assertion held.

var failures: Array[String] = []


func _check(ok: bool, label: String) -> void:
	if ok:
		print("  ok: %s" % label)
	else:
		failures.append(label)
		printerr("  FAIL: %s" % label)


func _initialize() -> void:
	# Failsafe: if _run aborts on a script error mid-way, the main loop
	# keeps spinning and would hang CI forever. This timer fires anyway.
	create_timer(90.0).timeout.connect(
		func() -> void:
			printerr("  FAIL: smoke test timed out (script error or hang)")
			quit(1)
	)
	# Defer so autoloads (Db, Store) are in the tree before we start.
	call_deferred("_run")


func _run() -> void:
	print("== Smoke test: booting main scene ==")
	var packed: PackedScene = load("res://scenes/main.tscn")
	_check(packed != null, "main.tscn loads")
	var main: Node = packed.instantiate()
	root.add_child(main)
	await process_frame
	await process_frame

	_check(root.get_node("/root/Store") != null, "Store autoload present")
	_check(root.get_node("/root/Db") != null, "Db autoload present")
	var db: Node = root.get_node("/root/Db")
	_check(db.dialogues.size() >= 4, "dialogues loaded (%d)" % db.dialogues.size())
	_check(db.quests.size() >= 4, "quests loaded (%d)" % db.quests.size())
	_check(main.player != null, "player node ready")
	_check(main.get_node("Gatekeeper") != null, "NPCs instantiated")

	# Drive a real conversation through main.gd's own start_dialogue path.
	var store: Node = root.get_node("/root/Store")
	var gatekeeper: Node = main.get_node("Gatekeeper")
	main.start_dialogue(gatekeeper)
	_check(main.runner != null, "dialogue started via main.gd")
	_check(main.dialogue_ui.visible, "dialogue UI visible")
	_check(not main.player.input_enabled, "player input locked during dialogue")

	_choose_containing(main, "brandy")
	_check(
		main.runner != null and main.runner.current_id == "opened_guile", "advanced to opened_guile"
	)
	var state: Dictionary = store.get_state()
	_check(state["quests"]["completed"].has("enter_the_vale"), "quest completed through UI path")
	_check("gate_opened" in state["flags"], "flag set through UI path")
	_choose_containing(main, "[Enter the camp]")
	_check(main.runner == null, "dialogue ended cleanly")
	_check(main.player.input_enabled, "player input restored")

	# Save, wipe, load — through the same systems the F5/F9 keys use.
	var save_path := "user://smoke_save.json"
	_check(SaveSystem.save_game(store.get_state(), save_path), "save written")
	store.reset()
	_check(not store.get_state()["quests"]["completed"].has("enter_the_vale"), "state wiped")
	_check(store.restore(SaveSystem.load_game(save_path)), "save restored")
	_check(
		store.get_state()["quests"]["completed"]["enter_the_vale"] == "guile",
		"progress survived round trip"
	)
	DirAccess.remove_absolute(save_path)

	# Painted scene: boot the Disco Elysium-style pipeline end to end.
	main.queue_free()
	await process_frame
	store.reset()
	var painted_packed: PackedScene = load("res://scenes/painted/prison_yard.tscn")
	_check(painted_packed != null, "prison_yard.tscn loads")
	var painted: Node = painted_packed.instantiate()
	root.add_child(painted)
	await process_frame
	await process_frame
	_check(painted.player != null, "painted scene built player from manifest")
	_check(painted.npcs.size() == 1, "painted scene placed NPCs")
	painted.start_dialogue(painted.npcs[0])
	_check(painted.runner != null, "painted scene dialogue started")
	_choose_containing(painted, "counted the keys")
	_check("ordo_compromised" in store.get_state()["flags"], "painted scene effect applied")
	_choose_containing(painted, "shadows of the yard")
	_check(painted.runner == null, "painted scene dialogue ended")

	# Let a few frames run so _process/_physics_process code paths execute.
	for i in 10:
		await process_frame
	print(
		(
			"== Smoke test: %s =="
			% ("PASSED" if failures.is_empty() else "FAILED (%d)" % failures.size())
		)
	)
	quit(0 if failures.is_empty() else 1)


func _choose_containing(main: Node, substring: String) -> void:
	var options: Array[Dictionary] = main.runner.visible_options(
		root.get_node("/root/Store").get_state()
	)
	for option in options:
		if option["available"] and substring in str(option["text"]):
			main._on_option_chosen(option["index"])
			return
	failures.append("no option containing '%s'" % substring)
	printerr("  FAIL: no option containing '%s'" % substring)
