## The player's skills (data/skills.json) and the checks the story makes against them.
##
## A passive check is free: the line is shown when skill + PASSIVE_BONUS reaches its number. An active
## check is two six-sided dice plus the skill against a difficulty; two sixes always succeed and two
## ones always fail. A "white" check that failed may be tried again once the skill has risen (or a
## flag the story names has been set); a "red" check is made once.
##
## The dice are drawn from the game's seed, the check's key and the attempt number, so a result is
## the same however often a save is loaded. Every result is kept in `rolls` and goes into the save.
##
##   main.skills.value("perception")   main.skills.add("logic", 1)   Skills.chance(3, 12)
extends RefCounted

signal changed(id: String)

const SceneData := preload("res://scripts/scene_data.gd")

const PASSIVE_BONUS := 6

var defs: Array = []            # [{id, name, description, color, value}] in sheet order
var difficulties: Array = []    # [{name, dc}] easiest first
var values := {}                # id -> current value
var rolls := {}                 # key -> {skill, dc, kind, success, dice, total, value, flag, attempts}
var dice_seed := 0
var archetype := ""             # the build the game began with (data/archetypes.json); "" when none was chosen


func load_defs(path: String) -> void:
	if not FileAccess.file_exists(SceneData.res(path)):
		push_warning("skills: no %s" % path)
		return
	var doc = SceneData._json(path)
	if not doc is Dictionary:
		return
	defs = doc.get("skills", [])
	difficulties = doc.get("difficulties", [])
	for d in defs:
		values[d.id] = int(d.get("value", 1))
	dice_seed = randi() & 0x7fffffff


# ---------- the skills ----------

func has_skill(id: String) -> bool:
	return values.has(id)


func ids() -> Array:
	return defs.map(func(d): return d.id)


func def(id: String) -> Dictionary:
	for d in defs:
		if d.id == id:
			return d
	return {}


func skill_name(id: String) -> String:
	return def(id).get("name", id.capitalize())


func color_of(id: String) -> Color:
	return Color(def(id).get("color", "#d9b77a"))


func value(id: String) -> int:
	return int(values.get(id, 0))


func set_value(id: String, v: int) -> void:
	if values.has(id) and values[id] != v:
		values[id] = v
		changed.emit(id)


func add(id: String, n: int) -> void:
	set_value(id, value(id) + n)


## Starts the game from a build ({skill id: value}, see archetypes.gd); `id` is its archetype
## ("custom" for one the player spent the points on). A skill the build leaves out keeps its value.
func apply_build(id: String, build: Dictionary) -> void:
	for sid in build:
		set_value(sid, clampi(int(build[sid]), 1, 5))
	archetype = id


# ---------- difficulties ----------

## A difficulty written as a number (12) or by name ("challenging"); 0 when it is neither.
func parse_dc(v) -> int:
	if v is int or v is float:
		return maxi(int(v), 0)
	var s := str(v).strip_edges()
	if s.is_valid_int():
		return maxi(s.to_int(), 0)
	for d in difficulties:
		if String(d.name).to_lower() == s.to_lower():
			return int(d.dc)
	return 0


## The named level a number falls in: the hardest one it reaches (Trivial below the first).
func difficulty_name(dc: int) -> String:
	var out: String = difficulties[0].name if not difficulties.is_empty() else str(dc)
	for d in difficulties:
		if dc >= int(d.dc):
			out = d.name
	return out


## Two six-sided dice plus `skill` against `dc`: the share of the 36 throws that succeed.
static func chance(skill: int, dc: int) -> float:
	var ok := 0
	for a in range(1, 7):
		for b in range(1, 7):
			ok += 1 if wins(a, b, skill, dc) else 0
	return ok / 36.0


static func wins(a: int, b: int, skill: int, dc: int) -> bool:
	if a == 6 and b == 6:
		return true
	if a == 1 and b == 1:
		return false
	return a + b + skill >= dc


## A passive check: shown when the skill alone reaches the number.
func passes(skill: String, dc: int) -> bool:
	return value(skill) + PASSIVE_BONUS >= dc


# ---------- active checks ----------

## A failed white check may be tried again after the skill has risen, or once `flag_now` (the flag
## the story ties to the check) is set where it was not at the failure. Red checks never.
func may_retry(rec: Dictionary, flag_now := false) -> bool:
	if rec.success or rec.kind == "red":
		return false
	return value(rec.skill) > int(rec.value) or (flag_now and not rec.flag)


## What the dialogue shows for a check: {chance, passed, failed, locked}. `locked` is a failure
## that may not be tried again yet.
func state_of(key: String, skill: String, dc: int, flag_now := false) -> Dictionary:
	var out := {chance = chance(value(skill), dc), passed = false, failed = false, locked = false}
	var rec = rolls.get(key)
	if rec != null:
		out.passed = rec.success
		out.failed = not rec.success
		out.locked = out.failed and not may_retry(rec, flag_now)
	return out


## Makes the check, or returns the result kept under `key` when there is one that may not be
## made again. `fresh` is true when dice were thrown now.
func roll(key: String, skill: String, dc: int, kind: String, flag_now := false) -> Dictionary:
	var rec = rolls.get(key)
	if rec != null and not may_retry(rec, flag_now):
		var kept: Dictionary = rec.duplicate()
		kept.fresh = false
		return kept
	var attempt: int = int(rec.attempts) + 1 if rec != null else 1
	var rng := RandomNumberGenerator.new()
	rng.seed = ("0x" + ("%d|%s|%d" % [dice_seed, key, attempt]).md5_text().left(12)).hex_to_int()
	var a := rng.randi_range(1, 6)
	var b := rng.randi_range(1, 6)
	var v := value(skill)
	var made := {skill = skill, dc = dc, kind = kind, success = wins(a, b, v, dc), dice = [a, b],
		total = a + b + v, value = v, flag = flag_now, attempts = attempt}
	rolls[key] = made
	var out: Dictionary = made.duplicate()
	out.fresh = true
	return out


# ---------- the save ----------

func to_dict() -> Dictionary:
	return {seed = dice_seed, archetype = archetype, values = values.duplicate(), rolls = rolls.duplicate(true)}


## JSON has one number type; the integers come back as integers. A skill the save does not know
## starts at its default.
func from_dict(d: Dictionary) -> void:
	if d.is_empty():
		return
	dice_seed = int(d.get("seed", dice_seed))
	archetype = str(d.get("archetype", ""))
	for id in d.get("values", {}):
		if values.has(id):
			values[id] = int(d.values[id])
	rolls.clear()
	for key in d.get("rolls", {}):
		var r: Dictionary = d.rolls[key]
		rolls[key] = {skill = str(r.skill), dc = int(r.dc), kind = str(r.kind), success = bool(r.success),
			dice = [int(r.dice[0]), int(r.dice[1])], total = int(r.total), value = int(r.value),
			flag = bool(r.get("flag", false)), attempts = int(r.get("attempts", 1))}
