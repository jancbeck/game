## Music on the title screen: one looping track (config.json -> audio.menu_music, level
## audio.menu_music_db) on the "Music" bus. It fades in when the title opens and fades out over
## FADE_OUT_S once a game begins, from New game, Continue or Load.
##
## The player hangs under the scene tree's root, not under main: Continue and Load replace main
## (session.gd), and the music must keep fading through that swap.
##
##   Music.title(main)   Music.fade_out()
extends Node

const SceneData := preload("res://scripts/scene_data.gd")
const Settings := preload("res://scripts/settings.gd")

const BUS := "Music"
const FADE_IN_S := 3.0
const FADE_OUT_S := 10.0
const SILENT_DB := -60.0

static var _player: AudioStreamPlayer
static var _tween: Tween
static var _level_db := -8.0


## Starts the track (or brings it back to full level) for the title screen.
static func title(main: Node) -> void:
	var cfg: Dictionary = main.data.config.get("audio", {})
	var path := str(cfg.get("menu_music", ""))
	if path == "":
		return
	_level_db = float(cfg.get("menu_music_db", -8.0))
	if not is_instance_valid(_player):
		var file := SceneData.abs_path(path)
		if not FileAccess.file_exists(file):
			push_warning("music: %s is missing" % path)
			return
		var stream := AudioStreamMP3.load_from_file(file)
		if stream == null:
			return
		stream.loop = true
		_ensure_bus()
		_player = AudioStreamPlayer.new()
		_player.name = "Music"
		_player.bus = BUS
		_player.stream = stream
		_player.volume_db = SILENT_DB
		main.get_tree().root.add_child(_player)
	if not _player.playing:
		_player.play()
	_fade(_level_db, FADE_IN_S)


## Fades the track out and frees the player. Nothing happens when no music plays.
static func fade_out() -> void:
	if not is_instance_valid(_player) or not _player.playing:
		return
	var p := _player
	_fade(SILENT_DB, FADE_OUT_S).finished.connect(func():
		if p == _player and p.volume_db <= SILENT_DB + 0.1:
			p.stop())


static func playing() -> bool:
	return is_instance_valid(_player) and _player.playing


## Tweens the linear amplitude, so the fade sounds even rather than dropping away at the end.
static func _fade(to_db: float, seconds: float) -> Tween:
	if _tween and _tween.is_valid():
		_tween.kill()
	var from := db_to_linear(_player.volume_db)
	_tween = _player.create_tween()
	_tween.tween_method(func(a: float): _player.volume_db = linear_to_db(maxf(a, 0.00001)),
		from, db_to_linear(to_db), seconds)
	return _tween


static func _ensure_bus() -> void:
	if AudioServer.get_bus_index(BUS) == -1:
		AudioServer.add_bus()
		AudioServer.set_bus_name(AudioServer.bus_count - 1, BUS)
		AudioServer.set_bus_send(AudioServer.bus_count - 1, "Master")
	Settings.apply()
