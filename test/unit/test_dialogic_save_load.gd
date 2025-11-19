class_name TestDialogicSaveLoad
extends GdUnitTestSuite

const GameStateScript = preload("res://scripts/core/game_state.gd")

var _game_state_instance: GameStateScript


func before_test():
	_game_state_instance = GameStateScript.new()
	_game_state_instance._initialize_state()


func after_test():
	if _game_state_instance:
		_game_state_instance.free()


func test_dialogic_state_round_trips_through_game_state_save_and_restore():
	# Arrange - Capture initial Dialogic state
	var original_dialogic_state: Dictionary = Dialogic.get_full_state()
	
	# Act - Take snapshot via GameState
	var snapshot = _game_state_instance.snapshot_for_save()
	
	# Verify Dialogic state was captured in snapshot
	assert_that(snapshot).has_key("dialogic")
	assert_that(snapshot["dialogic"]).has_key("engine_state")
	
	# Mutate Dialogic to something different
	# Load empty state to change Dialogic's internal state
	Dialogic.load_full_state({})
	var mutated_state = Dialogic.get_full_state()
	assert_that(mutated_state).is_not_equal(original_dialogic_state)
	
	# Restore via GameState
	_game_state_instance.restore_from_save(snapshot)
	
	# Assert - Dialogic state restored
	var restored_dialogic_state = Dialogic.get_full_state()
	assert_that(restored_dialogic_state).is_equal(original_dialogic_state)
