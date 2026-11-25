## The journal: the tasks the story writes down. `# journal:<id>:<text>` on a line of the story opens
## the task or replaces its text, `# journal_done:<id>` closes it. Titles come from data/journal.json
## (a task without one is shown by its id). The entries go into the save.
##
##   main.journal.update("rider", "Marl wants the rider found.")   main.journal.finish("rider")
extends RefCounted

signal changed(id: String)

const SceneData := preload("res://scripts/scene_data.gd")

var titles := {}          # id -> title
var entries := {}         # id -> {id, text, done, at}
var _clock := 0


func load_titles(path: String) -> void:
	if not FileAccess.file_exists(SceneData.res(path)):
		return
	var doc = SceneData._json(path)
	for id in doc.get("quests", {}) if doc is Dictionary else {}:
		titles[id] = doc.quests[id].get("title", id)


func title(id: String) -> String:
	if titles.has(id):
		return titles[id]
	return id.replace("_", " ").capitalize()


## Opens the task or replaces its text. False when the text is the one it already has.
func update(id: String, text: String) -> bool:
	var e: Dictionary = entries.get(id, {})
	if not e.is_empty() and e.text == text:
		return false
	_clock += 1
	entries[id] = {id = id, text = text, done = e.get("done", false), at = _clock}
	changed.emit(id)
	return true


## Closes the task. False when there is no such open task.
func finish(id: String) -> bool:
	if not entries.has(id) or entries[id].done:
		return false
	_clock += 1
	entries[id].done = true
	entries[id].at = _clock
	changed.emit(id)
	return true


func has(id: String) -> bool:
	return entries.has(id)


func is_done(id: String) -> bool:
	return entries.get(id, {}).get("done", false)


## The open tasks, or the closed ones, the one touched last first.
func list(done: bool) -> Array:
	var out: Array = entries.values().filter(func(e): return e.done == done)
	out.sort_custom(func(a, b): return a.at > b.at)
	return out


## The entry written or closed last as {title, text}; {} when the journal is empty.
func latest() -> Dictionary:
	var best := {}
	for e in entries.values():
		if best.is_empty() or e.at > best.at:
			best = e
	return {} if best.is_empty() else {title = title(best.id), text = best.text}


func to_dict() -> Dictionary:
	return {entries = entries.duplicate(true), clock = _clock}


func from_dict(d: Dictionary) -> void:
	entries.clear()
	_clock = int(d.get("clock", 0))
	for id in d.get("entries", {}):
		var e: Dictionary = d.entries[id]
		entries[id] = {id = str(id), text = str(e.text), done = bool(e.done), at = int(e.get("at", 0))}
