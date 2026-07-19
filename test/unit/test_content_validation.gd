extends GdUnitTestSuite
## Validates ALL shipped content: every dialogue graph is well-formed and
## every cross-reference (nodes, quests, attributes, effect types) resolves.
## This is the test that catches "WRITER delivered broken data" at CI time.

const DbScript := preload("res://scripts/core/db.gd")
const KNOWN_EFFECTS := ["start_quest", "complete_quest", "set_flag", "apply_approach", "journal"]
const KNOWN_CUTSCENE_STEPS := ["wait", "line", "walk", "flag", "effects"]
const KNOWN_REQUIRES := [
	"attributes",
	"not_hardened",
	"flags",
	"not_flags",
	"quest_active",
	"quest_completed",
	"quest_not_completed",
]
const ATTRIBUTES := ["might", "guile", "lore", "heart"]

var dialogues: Dictionary
var quests: Dictionary


func before_test() -> void:
	dialogues = DbScript._load_dir("res://data/dialogues")
	quests = DbScript._load_dir("res://data/quests")


func test_content_loaded() -> void:
	assert_int(dialogues.size()).is_greater_equal(4)
	assert_int(quests.size()).is_greater_equal(4)


func test_every_dialogue_has_start_node() -> void:
	for id: String in dialogues:
		(
			assert_bool(dialogues[id]["nodes"].has("start"))
			. override_failure_message("%s missing start" % id)
			. is_true()
		)


func test_every_next_resolves() -> void:
	for id: String in dialogues:
		var nodes: Dictionary = dialogues[id]["nodes"]
		for node_id: String in nodes:
			for option: Dictionary in nodes[node_id].get("options", []):
				var next: String = option.get("next", "")
				if next != "":
					(
						assert_bool(nodes.has(next))
						. override_failure_message(
							"%s/%s -> missing node '%s'" % [id, node_id, next]
						)
						. is_true()
					)


func test_every_node_reachable_from_start() -> void:
	for id: String in dialogues:
		var nodes: Dictionary = dialogues[id]["nodes"]
		var seen := {"start": true}
		var frontier := ["start"]
		while not frontier.is_empty():
			var node_id: String = frontier.pop_back()
			for option: Dictionary in nodes[node_id].get("options", []):
				var next: String = option.get("next", "")
				if next != "" and nodes.has(next) and not seen.has(next):
					seen[next] = true
					frontier.append(next)
		for node_id: String in nodes:
			(
				assert_bool(seen.has(node_id))
				. override_failure_message("%s: node '%s' unreachable from start" % [id, node_id])
				. is_true()
			)


func test_effects_are_valid() -> void:
	for id: String in dialogues:
		var nodes: Dictionary = dialogues[id]["nodes"]
		for node_id: String in nodes:
			for option: Dictionary in nodes[node_id].get("options", []):
				for effect: Dictionary in option.get("effects", []):
					var where := "%s/%s" % [id, node_id]
					var type: String = effect.get("type", "")
					(
						assert_array(KNOWN_EFFECTS)
						. override_failure_message("%s: unknown effect '%s'" % [where, type])
						. contains([type])
					)
					if type in ["start_quest", "complete_quest"]:
						(
							assert_bool(quests.has(effect.get("quest", "")))
							. override_failure_message(
								"%s: unknown quest '%s'" % [where, effect.get("quest")]
							)
							. is_true()
						)
					if type == "apply_approach":
						(
							assert_array(ATTRIBUTES)
							. override_failure_message("%s: unknown attribute" % where)
							. contains([effect.get("attribute", "")])
						)


func test_requires_use_known_keys_and_attributes() -> void:
	for id: String in dialogues:
		var nodes: Dictionary = dialogues[id]["nodes"]
		for node_id: String in nodes:
			for option: Dictionary in nodes[node_id].get("options", []):
				var requires: Dictionary = option.get("requires", {})
				for key: String in requires:
					(
						assert_array(KNOWN_REQUIRES)
						. override_failure_message(
							"%s/%s: unknown requires key '%s'" % [id, node_id, key]
						)
						. contains([key])
					)
				for attr: String in requires.get("attributes", {}):
					assert_array(ATTRIBUTES).contains([attr])
				for attr: String in requires.get("not_hardened", []):
					assert_array(ATTRIBUTES).contains([attr])


func test_every_quest_is_completable_in_some_dialogue() -> void:
	var completable := {}
	for id: String in dialogues:
		for node_id: String in dialogues[id]["nodes"]:
			for option: Dictionary in dialogues[id]["nodes"][node_id].get("options", []):
				for effect: Dictionary in option.get("effects", []):
					if effect.get("type") == "complete_quest":
						completable[effect["quest"]] = true
	for quest_id: String in quests:
		(
			assert_bool(completable.has(quest_id))
			. override_failure_message("Quest '%s' can never be completed" % quest_id)
			. is_true()
		)


func test_quests_have_title_and_summary() -> void:
	for quest_id: String in quests:
		(
			assert_bool(quests[quest_id].has("title") and quests[quest_id].has("summary"))
			. override_failure_message("Quest '%s' missing title/summary" % quest_id)
			. is_true()
		)


func test_chapters_reference_real_scenes_and_valid_requires() -> void:
	var chapters: Dictionary = DbScript._load_chapters("res://data/chapters.json")
	var scenes: Dictionary = DbScript._load_dir("res://data/scenes")
	(
		assert_bool(chapters.has("acts"))
		. override_failure_message("chapters.json has no acts")
		. is_true()
	)
	assert_int((chapters["acts"] as Array).size()).is_greater_equal(2)
	for act: Dictionary in chapters["acts"]:
		for field: String in ["id", "title", "scene"]:
			(
				assert_bool(act.has(field))
				. override_failure_message("act missing '%s'" % field)
				. is_true()
			)
		(
			assert_bool(scenes.has(act["scene"]))
			. override_failure_message(
				"act '%s' -> unknown scene '%s'" % [act.get("id"), act.get("scene")]
			)
			. is_true()
		)
		_assert_requires_valid(act.get("requires", {}), "act %s" % act.get("id"))


func test_scene_exits_resolve_to_real_scenes() -> void:
	var scenes: Dictionary = DbScript._load_dir("res://data/scenes")
	for scene_id: String in scenes:
		for scene_exit: Dictionary in scenes[scene_id].get("exits", []):
			var to: String = scene_exit.get("to", "")
			(
				assert_bool(scenes.has(to))
				. override_failure_message("scene '%s' exit -> unknown scene '%s'" % [scene_id, to])
				. is_true()
			)
			_assert_requires_valid(
				scene_exit.get("requires", {}), "%s exit %s" % [scene_id, scene_exit.get("id", "?")]
			)


func test_baked_occluder_cards_match_manifests() -> void:
	var scenes: Dictionary = DbScript._load_dir("res://data/scenes")
	for scene_id: String in scenes:
		var occluders: Array = scenes[scene_id].get("occluders", [])
		if occluders.is_empty():
			continue
		var cards_path := "res://art/occluders/%s/cards.json" % scene_id
		(
			assert_bool(FileAccess.file_exists(cards_path))
			. override_failure_message("scene '%s': missing %s" % [scene_id, cards_path])
			. is_true()
		)
		if not FileAccess.file_exists(cards_path):
			continue
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(cards_path))
		var cards_ok: bool = parsed is Dictionary and (parsed as Dictionary).has("cards")
		(
			assert_bool(cards_ok)
			. override_failure_message("scene '%s': cards.json not valid JSON" % scene_id)
			. is_true()
		)
		if not cards_ok:
			continue
		var cards: Array = parsed["cards"]
		(
			assert_int(cards.size())
			. override_failure_message(
				"scene '%s': %d cards, want %d" % [scene_id, cards.size(), occluders.size()]
			)
			. is_equal(occluders.size())
		)
		for i: int in occluders.size():
			if i >= cards.size():
				break
			var where := "%s occluder %d" % [scene_id, i]
			var card: Dictionary = cards[i]
			var occluder: Dictionary = occluders[i]
			(
				assert_array(_to_ints(card.get("anchor", [])))
				. override_failure_message("%s: baked anchor mismatch" % where)
				. is_equal(_to_ints(occluder["anchor"]))
			)
			var bounds := _occluder_bounds(occluder["polygon"])
			var expected := [bounds.position.x, bounds.position.y, bounds.size.x, bounds.size.y]
			(
				assert_array(_to_ints(card.get("bounds", [])))
				. override_failure_message("%s: baked bounds mismatch" % where)
				. is_equal(expected)
			)
			var card_path := str(card.get("card", ""))
			(
				assert_bool(FileAccess.file_exists(card_path))
				. override_failure_message("%s: missing card %s" % [where, card_path])
				. is_true()
			)
			if not FileAccess.file_exists(card_path):
				continue
			var image := Image.load_from_file(card_path)
			(
				assert_bool(image != null)
				. override_failure_message("%s: cannot decode %s" % [where, card_path])
				. is_true()
			)
			if image == null:
				continue
			(
				assert_int(image.get_width())
				. override_failure_message("%s: card width != bounds width" % where)
				. is_equal(bounds.size.x)
			)
			(
				assert_int(image.get_height())
				. override_failure_message("%s: card height != bounds height" % where)
				. is_equal(bounds.size.y)
			)


func test_cutscenes_reference_real_scenes_and_valid_steps() -> void:
	var cutscenes: Dictionary = DbScript._load_dir("res://data/cutscenes")
	var scenes: Dictionary = DbScript._load_dir("res://data/scenes")
	assert_int(cutscenes.size()).is_greater_equal(1)
	for cutscene_id: String in cutscenes:
		var cutscene: Dictionary = cutscenes[cutscene_id]
		var scene_id: String = cutscene.get("scene", "")
		(
			assert_bool(scenes.has(scene_id))
			. override_failure_message(
				"cutscene '%s' -> unknown scene '%s'" % [cutscene_id, scene_id]
			)
			. is_true()
		)
		var actor_ids := {"player": true}
		for npc: Dictionary in scenes.get(scene_id, {}).get("npcs", []):
			actor_ids[str(npc.get("id", ""))] = true
		for step: Dictionary in cutscene.get("timeline", []):
			var where := "cutscene %s" % cutscene_id
			var type: String = step.get("type", "")
			(
				assert_array(KNOWN_CUTSCENE_STEPS)
				. override_failure_message("%s: unknown step type '%s'" % [where, type])
				. contains([type])
			)
			if type == "walk":
				(
					assert_bool(actor_ids.has(str(step.get("actor", ""))))
					. override_failure_message(
						"%s: walk actor '%s' not in scene" % [where, step.get("actor")]
					)
					. is_true()
				)
				assert_int((step.get("to", []) as Array).size()).is_greater_equal(2)
			if type == "flag":
				assert_bool(str(step.get("flag", "")).is_empty()).is_false()
			if type == "effects":
				for effect: Dictionary in step.get("effects", []):
					_assert_effect_valid(effect, where)


## Shared check for a single effect dict (used by cutscene effect steps):
## the type is known and any referenced quest/attribute exists.
func _assert_effect_valid(effect: Dictionary, where: String) -> void:
	var type: String = effect.get("type", "")
	(
		assert_array(KNOWN_EFFECTS)
		. override_failure_message("%s: unknown effect '%s'" % [where, type])
		. contains([type])
	)
	if type in ["start_quest", "complete_quest"]:
		(
			assert_bool(quests.has(effect.get("quest", "")))
			. override_failure_message("%s: unknown quest '%s'" % [where, effect.get("quest")])
			. is_true()
		)
	if type == "apply_approach":
		assert_array(ATTRIBUTES).override_failure_message("%s: unknown attribute" % where).contains(
			[effect.get("attribute", "")]
		)


## Shared check for a requires-block (used by dialogue options, scene exits,
## and chapter acts alike): every key is known and every attribute is real.
func _assert_requires_valid(requires: Dictionary, where: String) -> void:
	for key: String in requires:
		(
			assert_array(KNOWN_REQUIRES)
			. override_failure_message("%s: unknown requires key '%s'" % [where, key])
			. contains([key])
		)
	for attr: String in requires.get("attributes", {}):
		assert_array(ATTRIBUTES).contains([attr])
	for attr: String in requires.get("not_hardened", []):
		assert_array(ATTRIBUTES).contains([attr])


## Bounds of a manifest occluder polygon, reimplementing the runtime's
## Rect2i.expand math exactly: the origin is the componentwise min of all
## points and the end the componentwise max (but at least polygon[0]+1), so
## the max point itself is EXCLUDED from the covered pixel region.
func _occluder_bounds(polygon: Array) -> Rect2i:
	var bounds := Rect2i(int(polygon[0][0]), int(polygon[0][1]), 1, 1)
	for point: Array in polygon:
		bounds = bounds.expand(Vector2i(int(point[0]), int(point[1])))
	return bounds


## JSON numbers parse as floats; cast each element to int so array equality
## with the computed bounds/anchor compares values, not numeric types.
func _to_ints(value: Variant) -> Array:
	var result := []
	if value is Array:
		for item in value:
			result.append(int(item))
	return result
