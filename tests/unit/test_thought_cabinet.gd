extends GutTest

## Unit tests for ThoughtCabinet system

var cabinet: ThoughtCabinet


func before_each():
	cabinet = ThoughtCabinet.new()
	add_child_autofree(cabinet)


func test_thought_creation():
	var thought = ThoughtCabinet.Thought.new(
		"test_thought",
		"Test Thought",
		"A test thought for testing",
		5.0,
		{"logic": 2, "health": -5}
	)

	assert_eq(thought.id, "test_thought", "Thought should have correct id")
	assert_eq(thought.title, "Test Thought", "Thought should have correct title")
	assert_eq(
		thought.description,
		"A test thought for testing",
		"Thought should have correct description"
	)
	assert_eq(
		thought.internalize_time, 5.0, "Thought should have correct internalize time"
	)
	assert_has(thought.effects, "logic", "Thought should have logic effect")
	assert_eq(thought.effects["logic"], 2, "Logic effect should be 2")
	assert_eq(thought.effects["health"], -5, "Health effect should be -5")


func test_add_available_thought():
	var thought = ThoughtCabinet.Thought.new(
		"test", "Test", "Description", 1.0, {}
	)
	cabinet.add_available_thought(thought)

	assert_true(
		cabinet.has_available_thought("test"), "Should have the available thought"
	)


func test_internalize_thought():
	var thought = ThoughtCabinet.Thought.new(
		"test", "Test", "Description", 0.1, {"logic": 1}
	)
	cabinet.add_available_thought(thought)

	var result = cabinet.internalize_thought("test")
	assert_true(result, "Should successfully internalize thought")


func test_cannot_internalize_already_active():
	var thought = ThoughtCabinet.Thought.new(
		"test", "Test", "Description", 0.1, {"logic": 1}
	)
	cabinet.add_available_thought(thought)

	cabinet.internalize_thought("test")
	await wait_seconds(0.2)  # Wait for internalization

	var result = cabinet.internalize_thought("test")
	assert_false(result, "Should not internalize already active thought")


func test_cannot_internalize_nonexistent():
	var result = cabinet.internalize_thought("nonexistent")
	assert_false(result, "Should not internalize nonexistent thought")


func test_max_active_thoughts():
	# Add and internalize maximum number of thoughts
	for i in range(cabinet.MAX_ACTIVE_THOUGHTS + 1):
		var thought = ThoughtCabinet.Thought.new(
			"thought_%d" % i,
			"Thought %d" % i,
			"Description",
			0.1,
			{}
		)
		cabinet.add_available_thought(thought)
		cabinet.internalize_thought("thought_%d" % i)

	# Wait for internalization
	await wait_seconds(0.2)

	# Should only have MAX_ACTIVE_THOUGHTS active
	assert_eq(
		cabinet.get_active_thoughts().size(),
		cabinet.MAX_ACTIVE_THOUGHTS,
		"Should not exceed max active thoughts"
	)


func test_forget_thought():
	var thought = ThoughtCabinet.Thought.new(
		"test", "Test", "Description", 0.1, {"logic": 1}
	)
	cabinet.add_available_thought(thought)
	cabinet.internalize_thought("test")
	await wait_seconds(0.2)  # Wait for internalization

	var result = cabinet.forget_thought("test")
	assert_true(result, "Should successfully forget thought")
	assert_false(
		cabinet.is_thought_active("test"), "Thought should no longer be active"
	)


func test_cannot_forget_nonactive_thought():
	var result = cabinet.forget_thought("nonexistent")
	assert_false(result, "Should not forget nonexistent thought")


func test_get_total_effects():
	var thought1 = ThoughtCabinet.Thought.new(
		"thought1", "T1", "D1", 0.1, {"logic": 2, "health": -5}
	)
	var thought2 = ThoughtCabinet.Thought.new(
		"thought2", "T2", "D2", 0.1, {"logic": 1, "morale": 10}
	)

	cabinet.add_available_thought(thought1)
	cabinet.add_available_thought(thought2)
	cabinet.internalize_thought("thought1")
	cabinet.internalize_thought("thought2")
	await wait_seconds(0.2)  # Wait for internalization

	var effects = cabinet.get_total_effects()

	# logic should be 2 + 1 = 3
	assert_eq(effects.get("logic", 0), 3, "Logic effects should sum")
	# health should be -5
	assert_eq(effects.get("health", 0), -5, "Health effect should be correct")
	# morale should be 10
	assert_eq(effects.get("morale", 0), 10, "Morale effect should be correct")


func test_get_available_thoughts():
	var thought1 = ThoughtCabinet.Thought.new("t1", "T1", "D1", 1.0, {})
	var thought2 = ThoughtCabinet.Thought.new("t2", "T2", "D2", 1.0, {})

	cabinet.add_available_thought(thought1)
	cabinet.add_available_thought(thought2)

	var available = cabinet.get_available_thoughts()
	assert_eq(available.size(), 2, "Should have 2 available thoughts")


func test_get_active_thoughts():
	var thought = ThoughtCabinet.Thought.new(
		"test", "Test", "Description", 0.1, {}
	)
	cabinet.add_available_thought(thought)
	cabinet.internalize_thought("test")
	await wait_seconds(0.2)  # Wait for internalization

	var active = cabinet.get_active_thoughts()
	assert_eq(active.size(), 1, "Should have 1 active thought")


func test_thought_internalized_signal():
	var thought = ThoughtCabinet.Thought.new(
		"test", "Test", "Description", 0.1, {}
	)
	cabinet.add_available_thought(thought)

	watch_signals(cabinet)
	cabinet.internalize_thought("test")
	await wait_seconds(0.2)  # Wait for internalization

	assert_signal_emitted(
		cabinet, "thought_internalized", "Should emit thought internalized signal"
	)


func test_thought_forgotten_signal():
	var thought = ThoughtCabinet.Thought.new(
		"test", "Test", "Description", 0.1, {}
	)
	cabinet.add_available_thought(thought)
	cabinet.internalize_thought("test")
	await wait_seconds(0.2)  # Wait for internalization

	watch_signals(cabinet)
	cabinet.forget_thought("test")

	assert_signal_emitted(
		cabinet, "thought_forgotten", "Should emit thought forgotten signal"
	)
