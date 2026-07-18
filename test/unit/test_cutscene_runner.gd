extends GdUnitTestSuite
## The CutsceneRunner is pure sequencing + store effects — tested by driving a
## hand-built timeline and asserting order, effect application, and that visual
## steps never touch the store.

const StoreScript := preload("res://scripts/core/store.gd")

var store: Node


func before_test() -> void:
	store = auto_free(StoreScript.new())
	store.reset()


func _runner(timeline: Array) -> CutsceneRunner:
	return CutsceneRunner.new({"id": "t", "scene": "prison_yard", "timeline": timeline})


func test_empty_timeline_ends_immediately() -> void:
	var ended := [false]
	var cut := _runner([])
	cut.ended.connect(func() -> void: ended[0] = true)
	cut.start()
	assert_bool(cut.is_running()).is_false()
	assert_bool(ended[0]).is_true()


func test_timeline_advances_through_every_step_then_ends() -> void:
	var ended := [false]
	var cut := _runner([{"type": "wait"}, {"type": "line"}, {"type": "walk"}])
	cut.ended.connect(func() -> void: ended[0] = true)
	cut.start()
	var seen: Array = []
	while cut.is_running():
		seen.append(cut.current_step()["type"])
		cut.advance()
	assert_array(seen).is_equal(["wait", "line", "walk"])
	assert_bool(ended[0]).is_true()


func test_apply_runs_store_steps_and_leaves_visual_steps_to_the_driver() -> void:
	var cut := _runner([])
	# flag / effects mutate the store and report handled=true.
	assert_bool(cut.apply({"type": "flag", "flag": "gate_open"}, store)).is_true()
	assert_bool(Reducers.has_flag(store.get_state(), "gate_open")).is_true()
	(
		assert_bool(
			cut.apply({"type": "effects", "effects": [{"type": "journal", "text": "hi"}]}, store)
		)
		. is_true()
	)
	assert_array(store.get_state()["journal"]).contains(["hi"])
	# Visual steps report handled=false and never touch the store.
	assert_bool(cut.apply({"type": "walk", "actor": "player", "to": [1, 2]}, store)).is_false()
	assert_bool(cut.apply({"type": "line", "text": "x"}, store)).is_false()
	assert_bool(cut.apply({"type": "wait", "seconds": 1}, store)).is_false()


func test_full_run_applies_store_steps_in_order() -> void:
	var cut := _runner(
		[
			{"type": "wait", "seconds": 0.1},
			{"type": "flag", "flag": "escort_departed"},
			{"type": "effects", "effects": [{"type": "journal", "text": "left the yard"}]},
			{"type": "line", "text": "..."},
		]
	)
	cut.start()
	while cut.is_running():
		var step: Dictionary = cut.current_step()
		cut.apply(step, store)
		cut.advance()
	var state: Dictionary = store.get_state()
	assert_bool(Reducers.has_flag(state, "escort_departed")).is_true()
	assert_array(state["journal"]).contains(["left the yard"])
