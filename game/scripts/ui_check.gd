## Check run for the interface, with a window: the satchel with an item and its notice and the F1
## quest panel, the pad's selection label on a hotspot, a conversation with the first response
## highlighted for the pad, the character sheet and the journal, a conversation of skill voices
## and check options (fresh, failed and locked, passed), and a long log whose older lines fade
## above the newest one with the chances in bold. Saves screenshots to game/shots/.
##   Godot --path game --audio-driver Dummy -- --no-intro --ui-check
extends Node

const SystemsCheck := preload("res://scripts/systems_check.gd")
const Dialogue := preload("res://scripts/dialogue.gd")


func _ready() -> void:
	var m := get_parent()
	await get_tree().create_timer(2.0).timeout
	m.inventory.add("tally_stick")
	m.inventory_ui.toast("Taken: Tally stick")
	m.inventory_ui.open()
	m.quest_panel.show()
	await _shot("ui_satchel")
	m.inventory_ui.close()
	m.quest_panel.hide()
	m.pad.use_pad(true)
	m.player.global_position = m.nav.nav_point(Vector3(0.5, 0.0, 3.0))
	m.pad.select_step(Vector2.RIGHT)
	await get_tree().create_timer(0.5).timeout
	await _shot("ui_pad_select")
	m.pad.select_step(Vector2.RIGHT)
	await get_tree().create_timer(0.5).timeout
	await _shot("ui_pad_select2")
	m.interaction.set_selected(null)
	m.npcs[0].talk()
	await get_tree().create_timer(1.5).timeout
	await _shot("ui_dialogue_pad")
	m.ui.close()
	m.pad.use_pad(false)
	await _skills(m)
	get_tree().quit()


## The character sheet, the journal, and a conversation with skill checks.
func _skills(m: Node) -> void:
	var sk = m.skills
	m.journal.update("rider", "Marl wants to know who came through the gate tonight. Start at the stable.")
	m.journal.update("bell", "Somebody tied the bell rope up with a strip of linen.")
	m.journal.update("tally", "Count the spears on the rack.")
	m.journal.finish("tally")
	m.sheet_ui.open("sheet")
	m.sheet_ui.select(2)
	await get_tree().create_timer(0.3).timeout
	await _shot("ui_sheet")
	m.sheet_ui.open("journal")
	await get_tree().create_timer(0.3).timeout
	await _shot("ui_journal")
	m.sheet_ui.close()
	# a seed under which the first press fails and the count succeeds
	var press := Dialogue.check_key("showcase", "authority", 12, "white")
	var count := Dialogue.check_key("showcase", "logic", 10, "white")
	for seed in 500:
		sk.dice_seed = seed
		sk.rolls.clear()
		if not sk.roll(press, "authority", 12, "white").success and sk.roll(count, "logic", 10, "white").success:
			break
	sk.rolls.clear()
	var d := SystemsCheck.fixture_dialogue(m)
	m.ui.begin_conversation(m.npcs[0]._idle)
	d._begin("showcase", "marl", "")
	await get_tree().create_timer(2.5).timeout
	await _shot("ui_checks_offered")
	m.ui._pick(0)
	await get_tree().create_timer(2.0).timeout
	await _shot("ui_checks_failed")
	m.ui._pick(2)
	await get_tree().create_timer(2.0).timeout
	await _shot("ui_checks_rolled")
	m.ui.close()
	await _long_log(m)


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://shots"))
	get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path("res://shots/%s.png" % name))
	print("shot ", name)


## A long talk: the newest line at full brightness, older ones fading upward, and check options below.
func _long_log(m: Node) -> void:
	var ui = m.ui
	ui.begin_conversation(m.npcs[0]._idle)
	for l in [
		["Sergeant Marl", "Another one through the gate after dark. Either you're lost, or somebody sent you to count our spears."],
		["You", "Who are you?"],
		["Sergeant Marl", "Sergeant Marl. Thirty-one winters on this rock, and the rock is winning."],
		["You", "What is this place?"],
		["Sergeant Marl", "A gate, a wall, and eleven men who argue about the soup. We watch the road north. The road has done nothing interesting since the old king died."],
		["You", "Why do you keep the bell under your roof?"],
		["Sergeant Marl", "The last man who kept that bell in the rain let it rust silent. Ring it once for a rider, twice for trouble. Three times, and I'll want to know who taught you to count."],
	]:
		ui.say(l[0], l[1])
	ui.say_skill(m.skills.skill_name("authority"), m.skills.color_of("authority"), "Medium: Success", ui.WHITE_CHECK,
		"He has not stood up. A sergeant who stays seated is telling you exactly what he thinks of you.")
	ui.say("Sergeant Marl", "Mind how you go. The stairs are slick, and the lamp on the second landing has been out since the thaw.")
	ui.set_options([
		"Is there anything I can do?",
		{text = "Press him until he gives way.", tag = "Bearing · Challenging 12 · 17%", tag_color = ui.WHITE_CHECK, locked = false},
		{text = "Order him to open the stores.", tag = "Bearing · Formidable 13 · 8% · one try", tag_color = ui.RED_CHECK, locked = false},
		{text = "Count the spears on the rack.", tag = "Tally · Medium 10 · 72%", tag_color = ui.WHITE_CHECK, locked = false},
		"[Leave.]",
	], Callable())
	ui.set_options_visible(true)
	await get_tree().create_timer(2.5).timeout
	await _shot("ui_long_log")
	ui.close()
