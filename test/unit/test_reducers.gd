extends GdUnitTestSuite
## Reducers are pure functions — tested with no scene tree at all.

var state: Dictionary


func before_test() -> void:
	state = preload("res://scripts/core/store.gd").initial_state()


func test_initial_state_shape() -> void:
	assert_bool(state["player"]["attributes"].has("might")).is_true()
	assert_int(state["player"]["attributes"]["heart"]["score"]).is_equal(1)
	assert_int(state["player"]["attributes"]["heart"]["flexibility"]).is_equal(10)
	assert_array(state["quests"]["active"]).is_empty()


func test_start_and_complete_quest() -> void:
	state = Reducers.start_quest(state, "q1")
	assert_bool(Reducers.quest_active(state, "q1")).is_true()
	state = Reducers.complete_quest(state, "q1", "guile")
	assert_bool(Reducers.quest_active(state, "q1")).is_false()
	assert_bool(Reducers.quest_completed(state, "q1")).is_true()
	assert_str(state["quests"]["completed"]["q1"]).is_equal("guile")


func test_start_quest_is_idempotent() -> void:
	state = Reducers.start_quest(state, "q1")
	state = Reducers.start_quest(state, "q1")
	assert_int(state["quests"]["active"].size()).is_equal(1)


func test_completed_quest_cannot_restart_or_recomplete() -> void:
	state = Reducers.complete_quest(state, "q1", "might")
	state = Reducers.start_quest(state, "q1")
	assert_bool(Reducers.quest_active(state, "q1")).is_false()
	state = Reducers.complete_quest(state, "q1", "heart")
	assert_str(state["quests"]["completed"]["q1"]).is_equal("might")


func test_apply_approach_raises_used_and_hardens_others() -> void:
	state = Reducers.apply_approach(state, "might")
	assert_int(Reducers.attribute_score(state, "might")).is_equal(2)
	assert_int(state["player"]["attributes"]["might"]["flexibility"]).is_equal(10)
	for other: String in ["guile", "lore", "heart"]:
		assert_int(state["player"]["attributes"][other]["flexibility"]).is_equal(8)


func test_specialization_locks_out_other_attributes() -> void:
	# Five might approaches at default cost 2 drain the other three to 0.
	for i in 5:
		state = Reducers.apply_approach(state, "might")
	assert_int(Reducers.attribute_score(state, "might")).is_equal(6)
	assert_bool(Reducers.is_hardened(state, "guile")).is_true()
	assert_bool(Reducers.is_hardened(state, "lore")).is_true()
	assert_bool(Reducers.is_hardened(state, "heart")).is_true()
	assert_bool(Reducers.is_hardened(state, "might")).is_false()


func test_flexibility_never_goes_negative() -> void:
	for i in 20:
		state = Reducers.apply_approach(state, "might")
	assert_int(state["player"]["attributes"]["guile"]["flexibility"]).is_equal(0)


func test_balanced_play_stays_flexible() -> void:
	for attr: String in ["might", "guile", "lore", "heart"]:
		state = Reducers.apply_approach(state, attr)
	for attr: String in ["might", "guile", "lore", "heart"]:
		assert_bool(Reducers.is_hardened(state, attr)).is_false()
		assert_int(Reducers.attribute_score(state, attr)).is_equal(2)


func test_requirements_attributes_and_hardening() -> void:
	assert_bool(Reducers.requirements_met(state, {"attributes": {"might": 1}})).is_true()
	assert_bool(Reducers.requirements_met(state, {"attributes": {"might": 2}})).is_false()
	for i in 5:
		state = Reducers.apply_approach(state, "might")
	assert_bool(Reducers.requirements_met(state, {"not_hardened": ["heart"]})).is_false()
	assert_bool(Reducers.requirements_met(state, {"not_hardened": ["might"]})).is_true()


func test_requirements_flags_and_quests() -> void:
	state = Reducers.set_flag(state, "gate_opened")
	state = Reducers.start_quest(state, "q1")
	state = Reducers.complete_quest(state, "q0", "lore")
	assert_bool(Reducers.requirements_met(state, {"flags": ["gate_opened"]})).is_true()
	assert_bool(Reducers.requirements_met(state, {"not_flags": ["gate_opened"]})).is_false()
	assert_bool(Reducers.requirements_met(state, {"quest_active": ["q1"]})).is_true()
	assert_bool(Reducers.requirements_met(state, {"quest_completed": ["q0"]})).is_true()
	assert_bool(Reducers.requirements_met(state, {"quest_not_completed": ["q0"]})).is_false()
	assert_bool(Reducers.requirements_met(state, {})).is_true()


func test_apply_effects_dispatches_all_types() -> void:
	state = (
		Reducers
		. apply_effects(
			state,
			[
				{"type": "start_quest", "quest": "q1"},
				{"type": "set_flag", "flag": "f1"},
				{"type": "apply_approach", "attribute": "lore"},
				{"type": "journal", "text": "entry"},
				{"type": "complete_quest", "quest": "q1", "approach": "lore"},
			]
		)
	)
	assert_bool(Reducers.quest_completed(state, "q1")).is_true()
	assert_bool(Reducers.has_flag(state, "f1")).is_true()
	assert_int(Reducers.attribute_score(state, "lore")).is_equal(2)
	assert_array(state["journal"]).contains(["entry"])


func test_journal_log_is_newest_first_and_non_destructive() -> void:
	state = Reducers.add_journal_entry(state, "first")
	state = Reducers.add_journal_entry(state, "second")
	var log: Array = Reducers.journal_log(state)
	assert_array(log).is_equal(["second", "first"])
	# The selector must not reverse or otherwise mutate the stored journal.
	assert_array(state["journal"]).is_equal(["first", "second"])


func test_quest_log_lists_active_then_completed_with_approach() -> void:
	state = Reducers.start_quest(state, "q_active")
	state = Reducers.start_quest(state, "q_done")
	state = Reducers.complete_quest(state, "q_done", "guile")
	var rows: Array = Reducers.quest_log(state)
	assert_int(rows.size()).is_equal(2)
	assert_str(rows[0]["id"]).is_equal("q_active")
	assert_bool(rows[0]["done"]).is_false()
	assert_str(rows[1]["id"]).is_equal("q_done")
	assert_bool(rows[1]["done"]).is_true()
	assert_str(rows[1]["approach"]).is_equal("guile")


func test_quest_log_and_journal_log_empty_on_fresh_state() -> void:
	assert_array(Reducers.quest_log(state)).is_empty()
	assert_array(Reducers.journal_log(state)).is_empty()
