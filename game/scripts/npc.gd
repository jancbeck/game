## A person you can talk to: a figure on the walk, a talking portrait for the voiced lines, and a
## listening loop between them. What the person says is in the story (data/story/<id>.ink, knot
## talk_<id>); dialogue.gd plays it and asks this figure to speak the clips.
##
## data/npcs/<id>.json: id, name, position/face/stand (Godot metres), palette, assets (a folder
## with portrait.jpg, idle/ and per line <clip>.wav plus <clip>/0001.jpg... frames at fps), portrait,
## fps, and optionally
##   location   the location the person stands in (default: the start location)
##   knot       the story's entry knot (default talk_<id>)
##   fallback   {location, position, face, stand}: where the person stands instead while the
##              location above has no export
##   idle_clip  the model's clip played while standing (default "idle"; "stir", "sleep", "sit")
##   talk_clip  the clip blended in while a line plays (default "talk"; "sit_talk" for a person in a chair)
##   hit_height, hit_half_width  the click box in metres (default 1.85 and 0.35); a sleeper lies low
## Without assets the person talks in text only. Source material for the clips: characters/<id>/.
extends Node3D

const SceneData := preload("res://scripts/scene_data.gd")
const HIT_HALF_WIDTH_M := 0.35

var main
var def: Dictionary
var figure: Node3D
var voice: AudioStreamPlayer
var _frames: Array[Texture2D] = []
var _clip_t := -1.0
var _idle: Texture2D
var _idle_frames: Array[Texture2D] = []
var _idle_t := 0.0
var _t := 0.0


func setup(m, d: Dictionary) -> void:
	main = m
	def = d
	name = def.id
	figure = preload("res://scripts/player.gd").new()
	figure.model = def.get("model", "")      # characters/<model>/recipe.json; "" keeps the procedural figure
	figure.idle_clip = def.get("idle_clip", "idle")
	figure.talk_clip = def.get("talk_clip", "talk")
	for k in def.get("palette", {}):
		figure.palette[k] = Color(def.palette[k][0], def.palette[k][1], def.palette[k][2])
	figure.nav = main.nav
	add_child(figure)
	figure.global_position = SceneData.v3(def.position)
	figure.face(SceneData.v3(def.face))
	voice = AudioStreamPlayer.new()
	voice.bus = "Voice"
	add_child(voice)
	_idle = _texture(def.get("portrait", ""))
	main.ui.closed.connect(func():
		voice.stop()
		_clip_t = -1.0)


func display_name() -> String:
	return def.name


func stand_point() -> Vector3:
	return SceneData.v3(def.stand)


func head() -> Vector3:
	return figure.global_position + Vector3(0, 1.7, 0)


## True when screen px falls on the figure (a box from the feet to the top of the head).
func hit(px: Vector2) -> bool:
	var feet: Vector2 = main.screen_of(figure.global_position)
	var top: Vector2 = main.screen_of(figure.global_position + Vector3(0, float(def.get("hit_height", 1.85)), 0))
	var half: float = (main.screen_of(figure.global_position + main.cam.global_basis.x * float(def.get("hit_half_width", HIT_HALF_WIDTH_M))) - feet).length()
	return px.x > feet.x - half and px.x < feet.x + half and px.y > top.y and px.y < feet.y + 4.0


func talk() -> void:
	if _idle_frames.is_empty() and def.has("assets"):
		_idle_frames = _sequence("%s/idle" % def.assets)
	figure.face(main.player.global_position)
	main.player.face(figure.global_position)
	main.ui.begin_conversation(_idle)
	if main.dialogue.has_talk(self):
		main.dialogue.begin_talk(self)
	else:
		push_warning("story has no knot for %s" % def.id)
		main.ui.say(def.name, "...")
		main.ui.set_options([], Callable())


## Plays the voice clip and the talking portrait of one line; false when there is no clip.
var _speak_until := 0.0


func speak(clip: String) -> bool:
	_frames.clear()
	_clip_t = -1.0
	voice.stop()
	if not def.has("assets"):
		return false
	var dir := "%s/%s" % [def.assets, clip]
	var wav := SceneData.abs_path(dir + ".wav")
	if not FileAccess.file_exists(wav):
		return false
	voice.stream = AudioStreamWAV.load_from_file(wav)
	_frames = _sequence(dir)
	voice.play()
	_clip_t = 0.0
	_speak_until = Time.get_ticks_msec() / 1000.0 + voice.stream.get_length() + 0.2
	return true


## True while the line plays. Also ends after the clip's length: with the Dummy audio driver
## (headless checks) a player never reports that it finished.
func is_speaking() -> bool:
	return voice.playing and Time.get_ticks_msec() / 1000.0 < _speak_until


func stop_speaking() -> void:
	voice.stop()
	_clip_t = -1.0
	_idle_t = 0.0


func _process(delta: float) -> void:
	_t += delta
	if figure:
		figure.set_talking(_clip_t >= 0.0 and main.ui.is_open())
		if not figure.has_model() and not figure.walking:
			# the procedural figure breathes: a slow rise of the shoulders
			figure.scale = Vector3(1.0, 1.0 + 0.006 * sin(_t * 1.6), 1.0)
	if not main.ui.is_open() or not main.interaction.talking_npc == self:
		return
	if _clip_t >= 0.0:
		_clip_t += delta
		var k := int(_clip_t * float(def.get("fps", 25)))
		if k < _frames.size():
			main.ui.set_portrait(_frames[k])
			return
		_clip_t = -1.0
		_idle_t = 0.0
	# listening between lines
	if _idle_frames.is_empty():
		main.ui.set_portrait(_idle)
		return
	_idle_t += delta
	main.ui.set_portrait(_idle_frames[int(_idle_t * float(def.get("fps", 25))) % _idle_frames.size()])


func _sequence(dir: String) -> Array[Texture2D]:
	var out: Array[Texture2D] = []
	var i := 1
	while FileAccess.file_exists(SceneData.res("%s/%04d.jpg" % [dir, i])):
		out.append(_texture("%s/%04d.jpg" % [dir, i]))
		i += 1
	return out


func _texture(path: String) -> Texture2D:
	if path == "" or not FileAccess.file_exists(SceneData.res(path)):
		return null
	var img := Image.load_from_file(SceneData.abs_path(path))
	return ImageTexture.create_from_image(img) if img else null
