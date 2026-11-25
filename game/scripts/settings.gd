## The player's settings, kept in user://settings.json: five volumes (master, voice, ambience,
## effects, music), the pace of text, whether lines follow each other on their own, fullscreen, and which
## hints (mouse and keys, or controller) the panels show.
##
## Everything is static, so the values survive the rebuild of the world on a change of location.
## The first read loads the file; `set_value` applies and saves. The master, voice, effects and
## music volumes sit on the buses of the same name; the ambience bus also follows the zoom and the
## ducking under a voice (audio.gd), so audio.gd adds `db("ambience")` to what it computes.
##
##   Settings.set_value("voice", 0.5)   Settings.volume("master")   Settings.chars_per_second()
extends RefCounted

const VOLUMES := ["master", "voice", "ambience", "effects", "music"]
const BUS_OF := {master = "Master", voice = "Voice", effects = "Sfx", music = "Music"}
## Characters revealed per second for each pace of text; 0 shows a line at once.
const TEXT_SPEEDS := {instant = 0.0, fast = 110.0, normal = 60.0, slow = 30.0}
const HINTS := ["auto", "mouse", "pad"]

static var path := "user://settings.json"
static var values := {}
static var _loaded := false


static func defaults() -> Dictionary:
	return {
		master = 1.0,
		voice = 1.0,
		ambience = 1.0,
		effects = 1.0,
		music = 1.0,
		text_speed = "fast",
		auto_advance = true,
		fullscreen = false,
		hints = "auto",
	}


## Reads the file over the defaults; a key that is missing or of the wrong kind keeps its default.
static func load_file() -> void:
	values = defaults()
	_loaded = true
	if not FileAccess.file_exists(path):
		return
	var d = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not d is Dictionary:
		push_warning("%s is not a settings file" % path)
		return
	for k in values:
		if d.has(k):
			values[k] = _clean(k, d[k], values[k])


static func _clean(key: String, v, fallback):
	if key in VOLUMES:
		return clampf(float(v), 0.0, 1.0) if v is float or v is int else fallback
	if key == "text_speed":
		return v if v is String and TEXT_SPEEDS.has(v) else fallback
	if key == "hints":
		return v if v is String and v in HINTS else fallback
	return bool(v) if v is bool else fallback


static func _ensure() -> void:
	if not _loaded:
		load_file()


static func get_value(key: String):
	_ensure()
	return values.get(key)


## Sets, applies and saves one setting. A value of the wrong kind is ignored.
static func set_value(key: String, v) -> void:
	_ensure()
	if not values.has(key):
		push_error("settings: no setting '%s'" % key)
		return
	values[key] = _clean(key, v, values[key])
	apply()
	save()


static func save() -> bool:
	_ensure()
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		push_error("cannot write %s (error %d)" % [path, FileAccess.get_open_error()])
		return false
	f.store_string(JSON.stringify(values, "\t"))
	return true


# ---------- reading ----------

## 0 to 1.
static func volume(name: String) -> float:
	_ensure()
	return float(values.get(name, 1.0))


static func db(name: String) -> float:
	var v := volume(name)
	return -80.0 if v <= 0.001 else linear_to_db(v)


static func chars_per_second() -> float:
	_ensure()
	return float(TEXT_SPEEDS.get(values.text_speed, 0.0))


static func auto_advance() -> bool:
	_ensure()
	return values.auto_advance


## Whether panels name the controller's buttons: always, never, or (auto) while a pad is in use.
static func pad_hints(pad_in_use: bool) -> bool:
	_ensure()
	match values.hints:
		"pad":
			return true
		"mouse":
			return false
	return pad_in_use


# ---------- applying ----------

## Puts the volumes on their buses and the window in its mode. A bus that does not exist yet
## (audio.gd makes them) is skipped; audio.gd applies again once they do.
static func apply() -> void:
	_ensure()
	for key in BUS_OF:
		var i := AudioServer.get_bus_index(BUS_OF[key])
		if i >= 0:
			AudioServer.set_bus_volume_db(i, db(key))
	if DisplayServer.get_name() == "headless":
		return
	var want := DisplayServer.WINDOW_MODE_FULLSCREEN if values.fullscreen else DisplayServer.WINDOW_MODE_WINDOWED
	if DisplayServer.window_get_mode() != want:
		DisplayServer.window_set_mode(want)
