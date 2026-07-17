extends GdUnitTestSuite
## Save/load round-trips through JSON, including int normalization.

const StoreScript := preload("res://scripts/core/store.gd")
const TEST_PATH := "user://test_save.json"


func after_test() -> void:
	if FileAccess.file_exists(TEST_PATH):
		DirAccess.remove_absolute(TEST_PATH)


func test_round_trip_preserves_state() -> void:
	var state := StoreScript.initial_state()
	state = Reducers.apply_approach(state, "guile")
	state = Reducers.start_quest(state, "q1")
	state = Reducers.complete_quest(state, "q0", "guile")
	state = Reducers.set_flag(state, "gate_opened")
	assert_bool(SaveSystem.save_game(state, TEST_PATH)).is_true()
	var loaded := SaveSystem.load_game(TEST_PATH)
	assert_bool(loaded.is_empty()).is_false()
	assert_int(Reducers.attribute_score(loaded, "guile")).is_equal(2)
	assert_int(loaded["player"]["attributes"]["might"]["flexibility"]).is_equal(8)
	assert_bool(Reducers.quest_active(loaded, "q1")).is_true()
	assert_str(loaded["quests"]["completed"]["q0"]).is_equal("guile")
	assert_bool(Reducers.has_flag(loaded, "gate_opened")).is_true()
	# JSON floats must come back as ints so score comparisons behave.
	assert_bool(loaded["player"]["attributes"]["guile"]["score"] is int).is_true()


func test_loaded_state_passes_store_validation() -> void:
	SaveSystem.save_game(StoreScript.initial_state(), TEST_PATH)
	var store: Node = auto_free(StoreScript.new())
	store.reset()
	assert_bool(store.restore(SaveSystem.load_game(TEST_PATH))).is_true()


func test_missing_and_corrupt_files() -> void:
	assert_bool(SaveSystem.load_game("user://does_not_exist.json").is_empty()).is_true()
	var file := FileAccess.open(TEST_PATH, FileAccess.WRITE)
	file.store_string("{not json")
	file.close()
	assert_bool(SaveSystem.load_game(TEST_PATH).is_empty()).is_true()


func test_store_rejects_malformed_state() -> void:
	var store: Node = auto_free(StoreScript.new())
	store.reset()
	assert_bool(store.restore({"garbage": true})).is_false()
