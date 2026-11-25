## The save files: `auto` (written at every change of location), `quick` (F5) and `slot_1` to
## `slot_8` (named by the player), one JSON file each in `dir`. A save is the dictionary of
## session.gd plus `meta`, which the lists read without loading a world:
##
##   meta {slot, name, location, quest {title, text}, when "YYYY-MM-DD HH:MM", unix}
##
## `quest` is the journal entry written last ({} when the journal is empty). A save made at the end
## of a chapter has `chapter_end` (the chapter's id) in its file, and `entries()` lists it as
## `chapter` in the meta. Checks point `dir` at a scratch folder so they never touch the player's saves.
extends RefCounted

const AUTO := "auto"
const QUICK := "quick"
const SLOT_COUNT := 8

static var dir := "user://saves"


## Every slot id, in the order the save screen lists them.
static func slot_ids() -> Array[String]:
	var out: Array[String] = [AUTO, QUICK]
	for i in SLOT_COUNT:
		out.append(slot_name(i + 1))
	return out


static func slot_name(n: int) -> String:
	return "slot_%d" % n


## The slots the player names (the save screen offers these).
static func named_slots() -> Array[String]:
	var out: Array[String] = []
	for i in SLOT_COUNT:
		out.append(slot_name(i + 1))
	return out


static func path_of(slot: String) -> String:
	return "%s/%s.json" % [dir, slot]


static func has(slot: String) -> bool:
	return FileAccess.file_exists(path_of(slot))


## The save in `slot`, or {} when there is none or it cannot be read.
static func read(slot: String) -> Dictionary:
	if not has(slot):
		return {}
	var d = JSON.parse_string(FileAccess.get_file_as_string(path_of(slot)))
	return d if d is Dictionary else {}


## Writes through a temporary file, so a crash never leaves half a save behind.
static func write(slot: String, d: Dictionary) -> bool:
	DirAccess.make_dir_recursive_absolute(dir)
	var tmp := path_of(slot) + ".tmp"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		push_error("cannot write %s (error %d)" % [tmp, FileAccess.get_open_error()])
		return false
	f.store_string(JSON.stringify(d, "\t"))
	f.close()
	return DirAccess.rename_absolute(tmp, path_of(slot)) == OK


static func delete(slot: String) -> void:
	if has(slot):
		DirAccess.remove_absolute(path_of(slot))


## The meta of every save that can be read, newest first.
static func entries() -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	for slot in slot_ids():
		var d := read(slot)
		if d.is_empty():
			continue
		var m: Dictionary = d.get("meta", {}).duplicate()
		m.slot = slot
		m.location = str(d.get("location", m.get("location", "")))
		m.chapter = str(d.get("chapter_end", ""))
		out.append(m)
	out.sort_custom(func(a, b): return float(a.get("unix", 0)) > float(b.get("unix", 0)))
	return out


## The newest save's meta, or {}.
static func latest() -> Dictionary:
	var all := entries()
	return all[0] if not all.is_empty() else {}


## The text a list shows for the save's quest: "Title: text" or "No tasks yet".
static func quest_line(m: Dictionary) -> String:
	var q: Dictionary = m.get("quest", {})
	if q.is_empty():
		return "No tasks yet"
	return "%s: %s" % [q.title, q.text]


## What a slot is called before the player names it, and in the lists when it has no name.
static func label_of(m: Dictionary) -> String:
	var n := str(m.get("name", ""))
	if n != "":
		return n
	match str(m.get("slot", "")):
		AUTO:
			return "Autosave"
		QUICK:
			return "Quick save"
	return "Save"


## The local date and time as written in the lists, and the same instant as a number for sorting.
static func stamp() -> Dictionary:
	return {when = Time.get_datetime_string_from_system(false, true).left(16), unix = Time.get_unix_time_from_system()}
