## The builds a new game offers (data/archetypes.json): named distributions of the skills, and the
## rules for a custom one. A build is {skill id: value}. Every build, preset or custom, has the
## same total: `low` for each skill plus `points` to spend, no skill above `high`.
##
##   var a := Archetypes.new(); a.load_file("data/archetypes.json", skills.ids())
##   a.find("ledger").skills   a.valid(build)   a.left(build)
extends RefCounted

const SceneData := preload("res://scripts/scene_data.gd")

var points := 12
var low := 1
var high := 5
var defs: Array = []            # [{id, name, description, skills}]
var custom := {name = "Custom", description = ""}
var skill_ids: Array = []


## Reads the file and reports (push_error) every build that breaks the rules.
func load_file(path: String, ids: Array) -> void:
	skill_ids = ids
	if not FileAccess.file_exists(SceneData.res(path)):
		push_warning("archetypes: no %s" % path)
		return
	var doc = SceneData._json(path)
	if not doc is Dictionary:
		return
	points = int(doc.get("points", points))
	low = int(doc.get("min", low))
	high = int(doc.get("max", high))
	defs = doc.get("archetypes", [])
	custom = doc.get("custom", custom)
	for d in defs:
		for msg in problems(d.get("skills", {})):
			push_error("archetypes: %s: %s" % [d.get("id", "?"), msg])


func find(id: String) -> Dictionary:
	for d in defs:
		if d.id == id:
			return d
	return {}


## Points a build has spent above the minimum.
func spent(build: Dictionary) -> int:
	var n := 0
	for id in skill_ids:
		n += int(build.get(id, low)) - low
	return n


## Points a build has left to spend (negative when it overspends).
func left(build: Dictionary) -> int:
	return points - spent(build)


## What is wrong with a build: a skill missing or out of range, the wrong total.
func problems(build: Dictionary) -> Array[String]:
	var out: Array[String] = []
	for id in skill_ids:
		if not build.has(id):
			out.append("no value for %s" % id)
		elif int(build[id]) < low or int(build[id]) > high:
			out.append("%s is %s, not %d to %d" % [id, build[id], low, high])
	for id in build:
		if not id in skill_ids:
			out.append("%s is not a skill" % id)
	if out.is_empty() and left(build) != 0:
		out.append("spends %d points, not %d" % [spent(build), points])
	return out


func valid(build: Dictionary) -> bool:
	return problems(build).is_empty()


## A build with every skill at the minimum, for the custom screen to start from.
func blank() -> Dictionary:
	var b := {}
	for id in skill_ids:
		b[id] = low
	return b
