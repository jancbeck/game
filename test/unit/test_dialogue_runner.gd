extends GdUnitTestSuite
## DialogueRunner against a synthetic dialogue and a real Store instance.

const StoreScript := preload("res://scripts/core/store.gd")

const DIALOGUE := {
	"id": "test_dlg",
	"nodes":
	{
		"start":
		{
			"speaker": "Tester",
			"text": "Pick one.",
			"options":
			[
				{
					"text": "Open path",
					"effects": [{"type": "set_flag", "flag": "went_open"}],
					"next": "second"
				},
				{
					"text": "Gated path",
					"requires": {"attributes": {"might": 99}},
					"show_locked": true,
					"effects": [],
					"next": "second",
				},
				{
					"text": "Hidden path",
					"requires": {"flags": ["nope"]},
					"effects": [],
					"next": "second"
				},
			],
		},
		"second":
		{
			"speaker": "Tester",
			"text": "Done.",
			"options": [{"text": "Bye", "effects": [], "next": ""}]
		},
	},
}

var store: Node
var runner: DialogueRunner


func before_test() -> void:
	store = auto_free(StoreScript.new())
	store.reset()
	runner = DialogueRunner.new(DIALOGUE)
	runner.start()


func test_visible_options_filters_and_greys() -> void:
	var options := runner.visible_options(store.get_state())
	# Open path visible+available; gated path visible but locked; hidden path absent.
	assert_int(options.size()).is_equal(2)
	assert_bool(options[0]["available"]).is_true()
	assert_bool(options[1]["available"]).is_false()


func test_choose_applies_effects_and_advances() -> void:
	runner.choose(0, store)
	assert_bool(Reducers.has_flag(store.get_state(), "went_open")).is_true()
	assert_str(runner.current_id).is_equal("second")


func test_choose_locked_option_is_rejected() -> void:
	runner.choose(1, store)
	assert_str(runner.current_id).is_equal("start")


func test_dialogue_ends_on_empty_next() -> void:
	var ended_seen: Array = []
	runner.ended.connect(func() -> void: ended_seen.append(true))
	runner.choose(0, store)
	runner.choose(0, store)
	assert_bool(runner.is_running()).is_false()
	assert_int(ended_seen.size()).is_equal(1)


func test_store_dispatch_ignores_bad_reducer_result() -> void:
	var before: Dictionary = store.get_state()
	store.dispatch(func(_s: Dictionary) -> Variant: return null)
	assert_bool(store.get_state().hash() == before.hash()).is_true()


func test_store_state_is_a_copy() -> void:
	var leaked: Dictionary = store.get_state()
	leaked["flags"].append("tampered")
	assert_bool(Reducers.has_flag(store.get_state(), "tampered")).is_false()
