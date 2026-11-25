## Headless smoke test of the game: loads main.tscn, runs it for FRAMES frames, checks that the
## data loaded and the main parts exist, runs systems_check.gd (story, pad, save, locations),
## prints one SMOKE line and quits with 0 or 1.
##
##   Godot --headless --path game --script res://scripts/smoke.gd
##
## scripts/game.py check runs it and also fails on any SCRIPT ERROR in the output.
extends SceneTree

const FRAMES := 90

const SystemsCheck := preload("res://scripts/systems_check.gd")
const Playthrough := preload("res://scripts/playthrough_check.gd")

var main: Node
var frames := 0
var _checking := false


func _initialize() -> void:
	preload("res://scripts/menu_ui.gd").enabled = false      # the checks play the world, not the title
	var packed: PackedScene = load("res://main.tscn")
	if packed == null:
		printerr("SMOKE cannot load res://main.tscn")
		quit(1)
		return
	main = packed.instantiate()
	root.add_child(main)


func _process(_delta: float) -> bool:
	frames += 1
	if main == null or frames < FRAMES or _checking:
		return false
	_checking = true
	_finish()
	return false


func _finish() -> void:
	var problems: Array[String] = []
	var data = main.get("data")
	if data == null or data.scene.is_empty():
		problems.append("scene.json did not load")
	elif data.hotspots.is_empty():
		problems.append("hotspots.json did not load")
	for part in ["view", "compositor", "nav", "player", "ui", "interaction", "audio", "session", "story", "dialogue", "pad", "inventory_ui"]:
		if main.get(part) == null:
			problems.append("main.%s is missing" % part)
	var hotspots: int = data.hotspots.size() if data != null else 0
	# the sound of the place: rain outside; inside no rain, a room tone, and the fire of its own hearth
	var inside: bool = data != null and data.scene.get("rain", true) == false
	var au = main.get("audio")
	if au != null and (au.interior != inside or (au.room != null) != inside or (au.bed != null) == inside or au.fire_player == null):
		problems.append("audio: %s should have %s" % ["an interior" if inside else "the open yard",
			"a room tone and a fire but no rain bed" if inside else "the rain bed and a fire but no room tone"])
	# the systems check plays the courtyard (Marl, the bell, the cookhouse door); other locations
	# loaded with --data= get the load checks above only
	var other := Array(OS.get_cmdline_user_args()).any(func(a): return a.begins_with("--data="))
	if problems.is_empty() and not other:
		problems.append_array(await SystemsCheck.new().run(self))
	# the quest from New game to the end of the chapter, through clicks and responses, in all three locations
	if problems.is_empty() and not other:
		problems.append_array(await Playthrough.new().run(self))
	print("SMOKE %d frames, %d hotspots, %d nodes, %s" % [frames, hotspots, _count(root),
		"ok" if problems.is_empty() else "; ".join(problems)])
	quit(0 if problems.is_empty() else 1)


func _count(n: Node) -> int:
	var c := 1
	for k in n.get_children():
		c += _count(k)
	return c
