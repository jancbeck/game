## The player's progress and how it moves between worlds: the location, the satchel, the quest
## flags, the skills and the rolls made against them, the journal and the visited places; the save
## file; and the change of location.
##
## The world of a location (view, compositor, navmesh, people) is built once by main.gd, so a change
## of location fades out, puts everything that must survive into a dictionary, and builds main.gd
## again from it. A save is that dictionary in user://save.json, so F9 and a door are one path.
##
## Save file (saves.gd keeps the slots): {version, location, player {pos, yaw}, inventory {id: n},
## vars {flag: value}, visited {location: true}, ink "<Ink state json>", skills {seed, archetype,
## values, rolls}, journal {entries}, chapter_end, meta}. A location change drops `player` and adds
## spawn {from, via}: the player arrives at the door of the new location that leads back to `from`.
## A change to the title screen is the dictionary {title: true}. `chapter_end` is the id of the chapter
## the game was saved at the end of (chapter_ui.gd): such a save loads to the chapter's card, not
## into the world.
extends Node

const SceneData := preload("res://scripts/scene_data.gd")
const Locations := preload("res://scripts/locations.gd")
const Inventory := preload("res://scripts/inventory.gd")
const Quest := preload("res://scripts/quest.gd")
const Skills := preload("res://scripts/skills.gd")
const Journal := preload("res://scripts/journal.gd")
const Archetypes := preload("res://scripts/archetypes.gd")
const Saves := preload("res://scripts/saves.gd")

const VERSION := 1
const PENDING_KEY := "game_pending_state"

static var fade_s := 0.45

var main
var location := ""
var inventory
var quest
var skills
var journal
var archetypes                # archetypes.gd: the builds a new game offers
var visited := {}
var skip_intro := false       # a world built from a save or a door starts at zoom 1
var traveling := false
var chapter_end := ""         # the chapter whose card the game stands at (chapter_ui.gd), "" in play
var placed := false           # the figure stands where it enters (it waits for the navmesh)
var _spawn := {}
var _ink := ""
var _fade_in := false
var _autosave := false


## The state a change of location or a load left for the world that is built next ({} on a fresh start).
static func take_pending() -> Dictionary:
	if not Engine.has_meta(PENDING_KEY):
		return {}
	var d: Dictionary = Engine.get_meta(PENDING_KEY)
	Engine.remove_meta(PENDING_KEY)
	return d


func setup(m, data: SceneData, pending: Dictionary) -> void:
	main = m
	location = data.location
	inventory = Inventory.new()
	inventory.load_defs(data.config.get("items", "data/items.json"))
	quest = Quest.new()
	skills = Skills.new()
	skills.load_defs(data.config.get("skills", "data/skills.json"))
	skills.from_dict(pending.get("skills", {}))
	archetypes = Archetypes.new()
	archetypes.load_file(data.config.get("archetypes", "data/archetypes.json"), skills.ids())
	journal = Journal.new()
	journal.load_titles(data.config.get("journal", "data/journal.json"))
	journal.from_dict(pending.get("journal", {}))
	inventory.from_dict(pending.get("inventory", {}))
	quest.extra = _ints(pending.get("vars", {}))
	visited = pending.get("visited", {})
	visited[location] = true
	_ink = pending.get("ink", "")
	_spawn = {player = pending.player} if pending.has("player") else pending.get("spawn", {})
	skip_intro = not pending.is_empty()
	_fade_in = pending.get("fade_in", false)
	_autosave = pending.get("autosave", false)
	chapter_end = str(pending.get("chapter_end", ""))


## JSON has one number type; whole numbers go back to ints.
static func _ints(d: Dictionary) -> Dictionary:
	var out := {}
	for k in d:
		var v = d[k]
		out[k] = int(v) if v is float and v == floorf(v) else v
	return out


func attach_story(story) -> void:
	quest.story = story
	story.restore(_ink)


# ---------- arriving ----------

## Puts the figure where it enters: at the saved spot, at the door that leads back to the location
## it came from, or at the start of the world; then fades in and autosaves after a change of location.
func arrive() -> void:
	if _fade_in:
		main.ui.fade.modulate.a = 1.0
	if _spawn.is_empty() and not _fade_in:
		placed = true
		return
	# the navmesh answers only after its first physics frame
	while not main.nav.ready_map():
		await get_tree().physics_frame
	var player: Node3D = main.player
	var nav = main.nav
	var at := Vector3.ZERO
	var look := Vector3.ZERO
	if _spawn.has("player"):
		var s: Dictionary = _spawn.player
		at = nav.nav_point(SceneData.v3(s.pos))
		look = at + Vector3(-sin(float(s.yaw)), 0.0, -cos(float(s.yaw)))
	elif _spawn.has("from"):
		var door := _door_to(_spawn.from)
		if door.is_empty():
			at = nav.nav_point(SceneData.v3(main.data.scene.get("walk", {}).get("start", [main.START.x, main.START.y, main.START.z])))
			look = at + Vector3(0, 0, -1)
		else:
			var out: Vector3 = nav.nav_point(door.pos)
			at = main.portals.step_out(out)
			look = at + (at - out)
			main.interaction.hold_exit(door.get("exit"))
	else:
		at = player.global_position
	player.global_position = at
	if look != Vector3.ZERO:
		player.face(look)
	placed = true
	if _autosave:
		save(Saves.AUTO)
	if chapter_end != "":
		main.chapter.begin(chapter_end, true)     # a save made at the end of a chapter: the world stays dark
		return
	if _fade_in:
		await get_tree().create_timer(0.3).timeout
		await main.ui.fade_to(0.0, 0.8)


## The door of this location that leads to `from`: {pos, exit?}.
func _door_to(from: String) -> Dictionary:
	for e in main.nav.exits:
		if e.target == from:
			return {pos = e.pos, exit = e}
	for pt in main.nav.portals:
		if pt.to == from:
			return {pos = pt.a}
	return {}


# ---------- the dictionary ----------

func capture() -> Dictionary:
	var d := {
		version = VERSION,
		location = location,
		inventory = inventory.to_dict(),
		vars = quest.extra.duplicate(),
		visited = visited.duplicate(),
		ink = main.story.state_json(),
		skills = skills.to_dict(),
		journal = journal.to_dict(),
	}
	var p: Vector3 = main.player.global_position
	d.player = {pos = [p.x, p.y, p.z], yaw = main.player.rotation.y}
	if chapter_end != "":
		d.chapter_end = chapter_end
	return d


# ---------- save and load ----------

## Writes the game to a slot of saves.gd: `quick` (F5), `auto`, or one of the named slots.
func save(slot := Saves.QUICK, save_name := "") -> bool:
	var d := capture()
	d.meta = _meta(slot, save_name)
	return Saves.write(slot, d)


## What the lists show about a save: where, when, and the task written last.
func _meta(slot: String, save_name: String) -> Dictionary:
	var m := Saves.stamp()
	m.slot = slot
	m.name = save_name
	m.location = location
	m.quest = journal.latest()
	return m


## Reads a save and rebuilds the world from it (after a fade). False when there is nothing usable.
func load_save(slot := Saves.QUICK) -> bool:
	if traveling:
		return false
	var d := Saves.read(slot)
	if d.is_empty() or int(d.get("version", 0)) != VERSION or not Locations.exists(main.data.config, str(d.get("location", ""))):
		push_warning("save '%s' is not usable" % slot)
		return false
	d.erase("meta")
	d.fade_in = true
	_go(d)
	return true


## Fades out and rebuilds the world as the title screen.
func to_title() -> bool:
	if traveling:
		return false
	_go({title = true, fade_in = true})
	return true


# ---------- locations ----------

func can_travel(target: String) -> bool:
	return Locations.exists(main.data.config, target)


## Fades out and enters `target` (a location name) by its door back to this one; `via` names the
## door used. False when `target` has no export, and nothing happens.
func travel(target: String, via := "") -> bool:
	if traveling or not can_travel(target):
		return false
	var d := capture()
	d.erase("player")
	d.location = target
	d.spawn = {from = location, via = via}
	d.fade_in = true
	d.autosave = true
	_go(d)
	return true


func _go(d: Dictionary) -> void:
	traveling = true
	main.ui.busy = true
	main.player.stop()
	await main.ui.fade_to(1.0, fade_s)
	Engine.set_meta(PENDING_KEY, d)
	Swap.run.call_deferred(main.get_parent(), main)


## Replaces the old main with a new one; static so the old one is gone before the call returns.
class Swap:
	static func run(parent: Node, old: Node) -> void:
		var tree := parent.get_tree()
		var was_current := tree.current_scene == old
		parent.remove_child(old)
		old.free()
		var next: Node = load(ProjectSettings.get_setting("application/run/main_scene")).instantiate()
		parent.add_child(next)
		if was_current:
			tree.current_scene = next
