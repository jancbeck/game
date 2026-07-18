class_name CutsceneRunner
extends RefCounted
## Plays one cutscene: an ordered timeline of steps loaded from
## data/cutscenes/<id>.json. Pure sequencing + store effects — the visual
## steps (wait, walk, line) are handed to a driver (painted_scene) to
## perform, while store-effect steps (flag, effects) are applied HERE through
## dispatch, exactly like DialogueRunner applies option effects. UI-free and
## unit-tested; there is no combat/scripting engine, only this timeline.
##
## Cutscene format:
## {
##   "id": "escort_departure",
##   "scene": "prison_yard",              # painted scene it plays in
##   "timeline": [
##     {"type": "wait", "seconds": 0.4},
##     {"type": "line", "speaker": "...", "text": "...",
##      "portrait": "res://..." (optional), "seconds": 1.6},
##     {"type": "walk", "actor": "player" | "<npc id>", "to": [px, py],
##      "face": [px, py] (optional), "speed": 2.6 (optional)},
##     {"type": "flag", "flag": "..."},              # sugar for a set_flag effect
##     {"type": "effects", "effects": [ ... ]}       # Reducers.apply_effects
##   ]
## }
## Recognised step types are enumerated in test_content_validation.gd —
## extend the runner, the validator, and the docs together or CI fails.

signal ended

var cutscene: Dictionary
var index := -1


func _init(data: Dictionary) -> void:
	cutscene = data


func timeline() -> Array:
	return cutscene.get("timeline", [])


func scene_id() -> String:
	return str(cutscene.get("scene", ""))


func is_running() -> bool:
	return index >= 0 and index < timeline().size()


func current_step() -> Dictionary:
	return timeline()[index] if is_running() else {}


## Begin at the first step (ending immediately on an empty timeline).
func start() -> void:
	index = 0 if not timeline().is_empty() else -1
	if index == -1:
		ended.emit()


## Apply a store-effect step (flag/effects) through dispatch. Returns true if
## the step mutated the store; false for a visual step (wait/line/walk) the
## driver must perform. Keeps all state mutation in one place, like
## DialogueRunner.choose — visual steps never touch the store.
func apply(step: Dictionary, store: Node) -> bool:
	match str(step.get("type", "")):
		"flag":
			var flag := str(step.get("flag", ""))
			store.dispatch(Reducers.apply_effects, [[{"type": "set_flag", "flag": flag}]])
			return true
		"effects":
			var effects: Array = step.get("effects", [])
			if not effects.is_empty():
				store.dispatch(Reducers.apply_effects, [effects])
			return true
	return false


## Advance to the next step; ends the cutscene when the timeline is exhausted.
func advance() -> void:
	if index < 0:
		return
	index += 1
	if index >= timeline().size():
		index = -1
		ended.emit()
