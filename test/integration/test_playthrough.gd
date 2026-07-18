extends GdUnitTestSuite
## Full playthroughs of the real shipped content at the logic level:
## Db data -> DialogueRunner -> Store. Proves the story is completable and
## that specialization lockouts actually bite in the finale.

const StoreScript := preload("res://scripts/core/store.gd")
const DbScript := preload("res://scripts/core/db.gd")

var store: Node
var dialogues: Dictionary


func before_test() -> void:
	store = auto_free(StoreScript.new())
	store.reset()
	dialogues = DbScript._load_dir("res://data/dialogues")


func _talk(dialogue_id: String, choice_substrings: Array) -> DialogueRunner:
	var runner := DialogueRunner.new(dialogues[dialogue_id])
	runner.start()
	for substring: String in choice_substrings:
		var picked := false
		for option in runner.visible_options(store.get_state()):
			if option["available"] and substring in str(option["text"]):
				runner.choose(option["index"], store)
				picked = true
				break
		(
			assert_bool(picked)
			. override_failure_message(
				(
					"No available option containing '%s' at %s/%s"
					% [substring, dialogue_id, runner.current_id]
				)
			)
			. is_true()
		)
	return runner


func test_guile_specialist_full_playthrough() -> void:
	# Act 1: gate via guile.
	_talk("gatekeeper", ["brandy", "[Enter the camp]"])
	var state: Dictionary = store.get_state()
	assert_str(state["quests"]["completed"]["enter_the_vale"]).is_equal("guile")
	assert_bool(Reducers.quest_active(state, "earn_your_place")).is_true()
	# Act 2: camp via guile (score is now 2, meets the gate).
	_talk("camp_leader", ["quartermaster", "look into it"])
	# Act 3: free Essek via guile.
	_talk("prisoner", ["rib bone", "vanish"])
	state = store.get_state()
	assert_bool(Reducers.has_flag(state, "knows_barrier_secret")).is_true()
	assert_bool(Reducers.quest_active(state, "confront_overseer")).is_true()
	assert_int(Reducers.attribute_score(state, "guile")).is_equal(4)
	# Finale: guile ending reachable, and the pure specialist is locked
	# out of every other ending (their attributes are too low anyway,
	# and flexibility loss has hardened them).
	var runner := _talk("overseer", ["I know what the barrier eats"])
	var options := runner.visible_options(store.get_state())
	var available_endings := 0
	for option in options:
		if option["available"] and "[" in str(option["text"]):
			available_endings += 1
	assert_int(available_endings).is_equal(1)
	runner = _talk("overseer", ["I know what the barrier eats", "partnership", "The Quiet Ledger"])
	state = store.get_state()
	assert_str(state["quests"]["completed"]["confront_overseer"]).is_equal("guile")
	assert_bool(Reducers.has_flag(state, "ending_partnership")).is_true()
	assert_bool(runner.is_running()).is_false()


func test_narrative_hud_reflects_playthrough_journal_and_quests() -> void:
	# The journal viewer + quest log (narrative HUD) read the store through
	# Reducers.journal_log / quest_log; drive real content and assert the
	# panel would show the recorded entries and quest state.
	_talk("gatekeeper", ["brandy", "[Enter the camp]"])
	var state: Dictionary = store.get_state()
	var journal: Array = Reducers.journal_log(state)
	# Newest entry first: the gate lie is the most recent thing recorded.
	assert_int(journal.size()).is_equal(1)
	assert_str(str(journal[0])).contains("brandy")
	var rows: Array = Reducers.quest_log(state)
	var by_id := {}
	for row: Dictionary in rows:
		by_id[row["id"]] = row
	assert_bool(by_id.has("enter_the_vale")).is_true()
	assert_bool(by_id["enter_the_vale"]["done"]).is_true()
	assert_str(by_id["enter_the_vale"]["approach"]).is_equal("guile")
	assert_bool(by_id.has("earn_your_place")).is_true()
	assert_bool(by_id["earn_your_place"]["done"]).is_false()


func test_specialist_is_hardened_out_of_offpath_options() -> void:
	_talk("gatekeeper", ["open you", "[Enter the camp]"])
	_talk("camp_leader", ["lift cage", "look into it"])
	_talk("prisoner", ["tear it free", "vanish"])
	var state: Dictionary = store.get_state()
	# Three might approaches: others at 10 - 6 = 4 flexibility, score 1.
	assert_int(Reducers.attribute_score(state, "might")).is_equal(4)
	assert_int(state["player"]["attributes"]["heart"]["flexibility"]).is_equal(4)
	# The heart ending needs score 3 — unreachable for this build.
	(
		assert_bool(
			Reducers.requirements_met(
				state, {"attributes": {"heart": 3}, "not_hardened": ["heart"]}
			)
		)
		. is_false()
	)


func test_heart_path_leaves_essek_chained_but_still_progresses() -> void:
	_talk("gatekeeper", ["How long have they kept you", "[Enter the camp]"])
	_talk("camp_leader", ["haven't sung", "look into it"])
	_talk("prisoner", ["people should know", "vigil"])
	var state: Dictionary = store.get_state()
	assert_bool(Reducers.has_flag(state, "essek_freed")).is_false()
	assert_bool(Reducers.has_flag(state, "essek_confessed")).is_true()
	assert_bool(Reducers.quest_active(state, "confront_overseer")).is_true()
	_talk("overseer", ["I know what the barrier eats", "deserve to choose", "The Vale That Chose"])
	assert_bool(Reducers.has_flag(store.get_state(), "ending_chosen")).is_true()


func test_overseer_stonewalls_without_the_secret() -> void:
	var runner := DialogueRunner.new(dialogues["overseer"])
	runner.start()
	for option in runner.visible_options(store.get_state()):
		assert_bool("barrier eats" in str(option["text"]) and option["available"]).is_false()


func test_prison_yard_jailer_scene() -> void:
	# The painted-scene demo content: every approach reaches the warning,
	# repeat conversations offer no second approach, and the scene
	# manifest wires to this dialogue.
	_talk("royal_jailer", ["counted the keys", "shadows of the yard"])
	var state: Dictionary = store.get_state()
	assert_bool(Reducers.has_flag(state, "ordo_heard_warning")).is_true()
	assert_bool(Reducers.has_flag(state, "ordo_compromised")).is_true()
	assert_int(Reducers.attribute_score(state, "guile")).is_equal(2)
	var runner := DialogueRunner.new(dialogues["royal_jailer"])
	runner.start()
	for option in runner.visible_options(store.get_state()):
		assert_bool("[Say nothing" in str(option["text"])).is_true()
	var scene: Dictionary = DbScript._load_dir("res://data/scenes")["prison_yard"]
	assert_str(str(scene["npcs"][0]["dialogue"])).is_equal("royal_jailer")


func test_save_load_mid_story_preserves_progress() -> void:
	_talk("gatekeeper", ["brandy", "[Enter the camp]"])
	var path := "user://test_mid_save.json"
	SaveSystem.save_game(store.get_state(), path)
	store.reset()
	assert_bool(Reducers.quest_active(store.get_state(), "earn_your_place")).is_false()
	assert_bool(store.restore(SaveSystem.load_game(path))).is_true()
	assert_bool(Reducers.quest_active(store.get_state(), "earn_your_place")).is_true()
	# Continue playing from the restored state to prove it's live, not inert.
	_talk("camp_leader", ["quartermaster", "look into it"])
	assert_bool(Reducers.has_flag(store.get_state(), "camp_member")).is_true()
	DirAccess.remove_absolute(path)
