extends GutTest

## Unit tests for CharacterStats system

var stats: CharacterStats


func before_each():
	stats = CharacterStats.new()
	add_child_autofree(stats)


func test_initial_attributes():
	assert_eq(stats.intellect, 2, "Initial intellect should be 2")
	assert_eq(stats.psyche, 2, "Initial psyche should be 2")
	assert_eq(stats.physique, 2, "Initial physique should be 2")
	assert_eq(stats.motorics, 2, "Initial motorics should be 2")


func test_skills_derived_from_attributes():
	# Skills should be calculated from attributes
	assert_eq(stats.logic, stats.intellect + 1, "Logic should be intellect + 1")
	assert_eq(
		stats.rhetoric, stats.intellect + stats.psyche, "Rhetoric should be intellect + psyche"
	)
	assert_eq(stats.empathy, stats.psyche + 1, "Empathy should be psyche + 1")
	assert_eq(
		stats.authority, stats.psyche + stats.physique, "Authority should be psyche + physique"
	)
	assert_eq(
		stats.perception, stats.motorics + stats.intellect, "Perception should be motorics + intellect"
	)
	assert_eq(stats.endurance, stats.physique + 1, "Endurance should be physique + 1")
	assert_eq(
		stats.pain_threshold, stats.physique + 1, "Pain threshold should be physique + 1"
	)
	assert_eq(
		stats.shivers, stats.psyche + stats.motorics, "Shivers should be psyche + motorics"
	)


func test_modify_attribute():
	var initial_intellect = stats.intellect
	stats.modify_attribute("intellect", 2)
	assert_eq(
		stats.intellect, initial_intellect + 2, "Intellect should increase by 2"
	)

	# Skills should update too
	assert_eq(
		stats.logic, stats.intellect + 1, "Logic should update with intellect change"
	)


func test_modify_attribute_minimum():
	stats.modify_attribute("intellect", -10)
	assert_eq(stats.intellect, 1, "Intellect should not go below 1")


func test_get_skill_value():
	assert_eq(stats.get_skill_value("logic"), stats.logic, "Should return correct skill value")
	assert_eq(
		stats.get_skill_value("rhetoric"), stats.rhetoric, "Should return correct skill value"
	)
	assert_eq(
		stats.get_skill_value("invalid_skill"), 1, "Should return 1 for invalid skill"
	)


func test_get_skill_value_case_insensitive():
	assert_eq(
		stats.get_skill_value("LOGIC"), stats.logic, "Should be case insensitive"
	)
	assert_eq(
		stats.get_skill_value("Logic"), stats.logic, "Should be case insensitive"
	)


func test_perform_skill_check():
	var result = stats.perform_skill_check("logic", 5)

	assert_has(result, "skill", "Result should contain skill name")
	assert_has(result, "skill_value", "Result should contain skill value")
	assert_has(result, "roll", "Result should contain roll")
	assert_has(result, "total", "Result should contain total")
	assert_has(result, "difficulty", "Result should contain difficulty")
	assert_has(result, "success", "Result should contain success boolean")
	assert_has(result, "margin", "Result should contain margin")

	assert_eq(result.skill, "logic", "Should have correct skill")
	assert_eq(result.difficulty, 5, "Should have correct difficulty")
	assert_between(result.roll, 2, 12, "Roll should be between 2 and 12 (2d6)")
	assert_eq(
		result.total, result.skill_value + result.roll, "Total should be skill + roll"
	)
	assert_eq(
		result.success, result.total >= result.difficulty, "Success should match calculation"
	)


func test_skill_check_signal():
	watch_signals(stats)
	stats.perform_skill_check("rhetoric", 8)
	assert_signal_emitted(stats, "skill_check_performed", "Should emit skill check signal")


func test_modify_health():
	stats.modify_health(-20)
	assert_eq(stats.health, 80, "Health should decrease")

	stats.modify_health(30)
	assert_eq(stats.health, 100, "Health should not exceed 100")

	stats.modify_health(-200)
	assert_eq(stats.health, 0, "Health should not go below 0")


func test_modify_morale():
	stats.modify_morale(-30)
	assert_eq(stats.morale, 70, "Morale should decrease")

	stats.modify_morale(50)
	assert_eq(stats.morale, 100, "Morale should not exceed 100")

	stats.modify_morale(-200)
	assert_eq(stats.morale, 0, "Morale should not go below 0")


func test_get_stats_summary():
	var summary = stats.get_stats_summary()
	assert_string_contains(summary, "CHARACTER STATS", "Should contain header")
	assert_string_contains(summary, "Intellect:", "Should contain intellect")
	assert_string_contains(summary, "Logic:", "Should contain skills")
	assert_string_contains(summary, "Health:", "Should contain health")
