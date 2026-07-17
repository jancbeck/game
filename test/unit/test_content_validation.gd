extends GdUnitTestSuite
## Validates ALL shipped content: every dialogue graph is well-formed and
## every cross-reference (nodes, quests, attributes, effect types) resolves.
## This is the test that catches "WRITER delivered broken data" at CI time.

const DbScript := preload("res://scripts/core/db.gd")
const KNOWN_EFFECTS := ["start_quest", "complete_quest", "set_flag", "apply_approach", "journal"]
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
