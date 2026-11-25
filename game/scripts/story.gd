## The Ink story (data/story/main.json, compiled from main.ink) behind every conversation and look
## text, on the inkgd runtime in addons/inkgd (Ink in pure GDScript). This wrapper is all the game
## knows about the runtime; the runtime classes are used untyped so the game still starts when
## they are not registered yet (see runtime_ready()).
extends RefCounted

const SceneData := preload("res://scripts/scene_data.gd")
const STORY_SCRIPT := "res://addons/inkgd/runtime/ink_story.gd"

var ink = null          # InkStory
var path := ""


## The runtime registers global classes, which Godot only learns from an editor scan or
## `Godot --headless --path game --import`.
static func runtime_ready() -> bool:
	if not Engine.get_main_loop().root.has_node("__InkRuntime"):
		return false
	for c in ProjectSettings.get_global_class_list():
		if c["class"] == "InkStory":
			return true
	return false


func load_file(story_path: String) -> bool:
	path = story_path
	if not FileAccess.file_exists(SceneData.res(path)):
		push_warning("story: no %s, conversations and look texts fall back to the data files" % path)
		return false
	if not runtime_ready():
		push_error("story: the Ink runtime is not registered; run `Godot --headless --path game --import` once")
		return false
	ink = load(STORY_SCRIPT).new(FileAccess.get_file_as_string(SceneData.res(path)))
	ink.on_error.connect(func(message, _type): push_error("ink: %s" % message))
	return true


func ok() -> bool:
	return ink != null


func has_knot(knot: String) -> bool:
	return ink != null and ink.has_function(knot)


func goto(knot: String) -> void:
	ink.choose_path_string(knot)


func can_continue() -> bool:
	return ink != null and ink.can_continue


## {text, tags, all}: the next line of output. tags is {key: value} from `# key:value` tags (the
## first of a key); all is every tag in order, [[key, value], ...].
func next_line() -> Dictionary:
	var text: String = ink.continue_story()
	var all: Array = ink.current_tags.map(_split_tag)
	var tags := {}
	for kv in all:
		if not tags.has(kv[0]):
			tags[kv[0]] = kv[1]
	return {text = text.strip_edges(), tags = tags, all = all}


## "key:value" -> [key, value]; a tag without a colon has an empty value.
static func _split_tag(t: String) -> Array:
	var i: int = t.find(":")
	if i < 0:
		return [t.strip_edges(), ""]
	return [t.substr(0, i).strip_edges(), t.substr(i + 1).strip_edges()]


func choices() -> Array:
	return ink.current_choices.map(func(c): return c.text)


## The choices with their tags: [{text, tags {key: value}, knot}]. Tags are the ones written inside
## the brackets of the choice, `+ [Say it #check:logic:8:white]`; knot is the knot the choice is in.
func choice_list() -> Array:
	return ink.current_choices.map(func(c):
		var tags := {}
		for t in (c.tags if c.tags != null else []):
			var kv := _split_tag(t)
			tags[kv[0]] = kv[1]
		return {text = c.text.strip_edges(), tags = tags, knot = str(c.source_path).split(".")[0]})


## The knot the story is running in ("" when it has no position).
func current_knot() -> String:
	var p = ink.state.current_path_string
	return str(p).split(".")[0] if p != null else ""


func choose(i: int) -> void:
	ink.choose_choice_index(i)


## Bind a game function to an EXTERNAL of the story. `pure` ones may be evaluated ahead of time.
func bind(name: String, object: Object, method: String, pure := false) -> void:
	ink.bind_external_function(name, object, method, pure)


# ---------- variables and state ----------

func variable_names() -> Array:
	return ink.variables_state.enumerate() if ink != null else []


func has_var(name: String) -> bool:
	return ink != null and ink.variables_state.global_variable_exists_with_name(name)


func get_var(name: String):
	return ink.variables_state.get_variable(name)


func set_var(name: String, value) -> void:
	ink.variables_state.set_variable(name, value)


## Variables, visit counts and position, as the JSON string Ink saves.
func state_json() -> String:
	return ink.state.to_json() if ink != null else ""


func restore(json: String) -> void:
	if ink != null and json != "":
		ink.state.load_json(json)
