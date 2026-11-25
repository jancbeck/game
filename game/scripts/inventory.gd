## What the player carries. Items are defined in data/items.json -> items, a list of
## {id, name, description, icon?}; icon is a path under game/ and is optional.
##
##   main.inventory.add("tally_stick")   main.inventory.has("tally_stick")   main.inventory.remove("tally_stick")
extends RefCounted

signal changed(id: String, delta: int)

const SceneData := preload("res://scripts/scene_data.gd")

var defs := {}       # id -> {id, name, description, icon?}
var counts := {}     # id -> how many, in the order the player got them


func load_defs(path: String) -> void:
	if not FileAccess.file_exists(SceneData.res(path)):
		return
	var doc = SceneData._json(path)
	for d in doc.get("items", []) if doc is Dictionary else []:
		defs[d.id] = d


## False when `id` is not defined in items.json.
func add(id: String, n := 1) -> bool:
	if not defs.has(id):
		push_error("inventory: unknown item '%s' (not in data/items.json)" % id)
		return false
	counts[id] = counts.get(id, 0) + n
	changed.emit(id, n)
	return true


func has(id: String) -> bool:
	return counts.get(id, 0) > 0


func count(id: String) -> int:
	return counts.get(id, 0)


## False when the player does not carry it.
func remove(id: String, n := 1) -> bool:
	if counts.get(id, 0) < n:
		return false
	counts[id] -= n
	if counts[id] <= 0:
		counts.erase(id)
	changed.emit(id, -n)
	return true


func list() -> Array:
	return counts.keys()


func item_name(id: String) -> String:
	return defs.get(id, {}).get("name", id)


func to_dict() -> Dictionary:
	return counts.duplicate()


## Ids that are no longer defined are dropped.
func from_dict(d: Dictionary) -> void:
	counts.clear()
	for id in d:
		if defs.has(id) and int(d[id]) > 0:
			counts[id] = int(d[id])
