## Check run for the title screen and its menus, with a window: the title with a Continue line, the
## new game screen with a preset build and with the custom points, the settings, the load list, the
## save list, and the pause menu. Saves screenshots to game/shots/ (menu_*.png). It writes its own
## saves and settings to scratch files, never the player's.
##   Godot --path game --audio-driver Dummy -- --menu-check
extends Node

const Saves := preload("res://scripts/saves.gd")
const Settings := preload("res://scripts/settings.gd")
const Session := preload("res://scripts/session.gd")


func _ready() -> void:
	var m := get_parent()
	Saves.dir = "user://saves_shots"
	Settings.path = "user://settings_shots.json"
	Settings.load_file()
	_fake_saves(m)
	m.menu.close()
	m.menu.open_title()
	await get_tree().create_timer(3.5).timeout
	await _shot("menu_title")
	m.menu._show("new_game")
	await get_tree().create_timer(0.6).timeout
	await _shot("menu_new_game")
	m.menu._pick_build("custom")
	for pair in [["perception", 4], ["logic", 5], ["composure", 3]]:
		m.menu._sliders[pair[0]].value = pair[1]
	m.menu._sliders["empathy"].grab_focus()
	await get_tree().create_timer(0.4).timeout
	await _shot("menu_new_game_custom")
	m.menu._show("settings")
	await get_tree().create_timer(0.6).timeout
	await _shot("menu_settings")
	m.menu._show("load")
	await get_tree().create_timer(0.6).timeout
	await _shot("menu_load")
	m.menu.close()
	m.menu.open_pause()
	await get_tree().create_timer(0.6).timeout
	await _shot("menu_pause")
	m.menu._show("save")
	await get_tree().create_timer(0.6).timeout
	await _shot("menu_save")
	_clean()
	get_tree().quit()


## Three saves from different hours, places and quests.
func _fake_saves(m: Node) -> void:
	var now := Time.get_unix_time_from_system()
	var rows := [
		["slot_1", "Before the stable", "courtyard", -86400.0 * 2, "The rider nobody rang for", "Somebody tied the bell rope up with a strip of linen."],
		["slot_2", "Hedda's soup", "cookhouse", -3600.0 * 5, "The commander's letter", "Tam is asleep in the north-west tower and will not give it up."],
		["auto", "", "cookhouse", -600.0, "The rider nobody rang for", "Hedda knows more than she says about the grey mare."],
	]
	for r in rows:
		var d: Dictionary = m.session.capture()
		d.location = r[2]
		var t: Dictionary = Time.get_datetime_dict_from_unix_time(int(now + r[3]))
		d.meta = {slot = r[0], name = r[1], location = r[2], unix = now + r[3],
			when = "%04d-%02d-%02d %02d:%02d" % [t.year, t.month, t.day, t.hour, t.minute],
			quest = {title = r[4], text = r[5]}}
		Saves.write(r[0], d)


func _clean() -> void:
	for slot in Saves.slot_ids():
		Saves.delete(slot)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Saves.dir))
	DirAccess.remove_absolute(ProjectSettings.globalize_path(Settings.path))


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://shots"))
	get_viewport().get_texture().get_image().save_png(ProjectSettings.globalize_path("res://shots/%s.png" % name))
	print("shot ", name)
