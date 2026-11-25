## The chapters of data/chapters.json: the card a chapter ends with and the page of the player's
## choices after it. The story ends a chapter with the external `end_chapter("<id>")`
## (dialogue.gd); chapter_ui.gd shows what this file reads out of the data and the game's state.
##
##   data/chapters.json  {chapters: {<id>: {title, body, summary: {title, lines [{var, label, values,
##                       default}], checks, next}}}}
extends RefCounted

const SceneData := preload("res://scripts/scene_data.gd")

var defs := {}


func load_file(path: String) -> void:
	if not FileAccess.file_exists(SceneData.res(path)):
		push_warning("chapters: no %s" % path)
		return
	var doc = SceneData._json(path)
	if doc is Dictionary:
		defs = doc.get("chapters", {})


func has(id: String) -> bool:
	return defs.has(id)


func def(id: String) -> Dictionary:
	return defs.get(id, {})


func title(id: String) -> String:
	return def(id).get("title", id.replace("_", " ").capitalize())


## The text a story variable's value stands for, as a dictionary key: a boolean as "true" or
## "false", a whole number without decimals, anything else as it is.
static func key_of(v) -> String:
	if v is bool:
		return "true" if v else "false"
	if v is float and v == floorf(v):
		return str(int(v))
	return str(v)


## The rows of the choices page: [{label, text}] in the order of the data. `read` is a
## Callable that answers the value of a story variable by its name.
static func rows(chapter: Dictionary, read: Callable) -> Array:
	var out := []
	for line in chapter.get("summary", {}).get("lines", []):
		var values: Dictionary = line.get("values", {})
		var text: String = values.get(key_of(read.call(str(line.var))), line.get("default", ""))
		if text != "":
			out.append({label = str(line.label), text = text})
	return out


## The checks made so far, in the order they were made, for the page's checks section:
## [{skill, dc, kind, success}] from skills.rolls.
static func checks(rolls: Dictionary) -> Array:
	return rolls.values().map(func(r): return {skill = r.skill, dc = int(r.dc), kind = r.kind, success = bool(r.success)})
