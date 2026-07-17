class_name DialogueRunner
extends RefCounted
## Runs one dialogue (a graph of nodes loaded from data/dialogues/*.json).
## Pure logic: reads state, applies option effects through the store's
## dispatch. Rendering is someone else's job (ui/dialogue_ui.gd).
##
## Dialogue format:
## {
##   "id": "gatekeeper",
##   "nodes": {
##     "start": {
##       "speaker": "Gatekeeper", "text": "...",
##       "options": [
##         {"text": "...", "next": "node_id" | "" (end),
##          "requires": {...},        # see Reducers.requirements_met
##          "effects": [{...}, ...],  # see Reducers.apply_effects
##          "show_locked": true}      # show greyed-out when unavailable
##       ]
##     }
##   }
## }

signal ended

var dialogue: Dictionary
var current_id: String = ""


func _init(dialogue_data: Dictionary) -> void:
	dialogue = dialogue_data


func start(node_id: String = "start") -> void:
	if not _nodes().has(node_id):
		push_error("Dialogue %s has no node '%s'" % [dialogue.get("id", "?"), node_id])
		ended.emit()
		return
	current_id = node_id


func is_running() -> bool:
	return current_id != ""


func current_node() -> Dictionary:
	return _nodes().get(current_id, {})


## Options the player can see for the current node, given state.
## Each entry: {index, text, available: bool}. Unavailable options are only
## included when the author sets show_locked (Disco Elysium-style greying).
func visible_options(state: Dictionary) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	var options: Array = current_node().get("options", [])
	for i in options.size():
		var option: Dictionary = options[i]
		var ok: bool = Reducers.requirements_met(state, option.get("requires", {}))
		if ok:
			result.append({"index": i, "text": option["text"], "available": true})
		elif option.get("show_locked", false):
			result.append({"index": i, "text": option["text"], "available": false})
	return result


## Pick an option by its index in the node's raw options array.
## Applies effects via the store and advances (or ends) the dialogue.
func choose(option_index: int, store: Node) -> void:
	var options: Array = current_node().get("options", [])
	if option_index < 0 or option_index >= options.size():
		push_error(
			"Bad option index %d in %s/%s" % [option_index, dialogue.get("id", "?"), current_id]
		)
		return
	var option: Dictionary = options[option_index]
	if not Reducers.requirements_met(store.get_state(), option.get("requires", {})):
		push_error(
			"Chose locked option %d in %s/%s" % [option_index, dialogue.get("id", "?"), current_id]
		)
		return
	var effects: Array = option.get("effects", [])
	if not effects.is_empty():
		store.dispatch(Reducers.apply_effects, [effects])
	var next: String = option.get("next", "")
	if next.is_empty() or not _nodes().has(next):
		current_id = ""
		ended.emit()
	else:
		current_id = next


func _nodes() -> Dictionary:
	return dialogue.get("nodes", {})
