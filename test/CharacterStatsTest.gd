class_name CharacterStatsTest
extends GdUnitTestSuite

## Unit test for CharacterStats class
## Tests individual stat calculations and skill check mechanics

var _character_stats: CharacterStats


func before_test():
	"""Initialize test data before each test case"""
	_character_stats = auto_free(CharacterStats.new())


func test_initial_attributes():
	"""Test that default attributes are set correctly"""
	assert_int(_character_stats.intellect).is_equal(2)
	assert_int(_character_stats.psyche).is_equal(2)
	assert_int(_character_stats.physique).is_equal(2)
	assert_int(_character_stats.motorics).is_equal(2)


func test_skill_calculation_from_attributes():
	"""Test that skills are correctly calculated from attributes"""
	# Logic should be intellect + 1
	assert_int(_character_stats.logic).is_equal(3)

	# Rhetoric should be intellect + psyche
	assert_int(_character_stats.rhetoric).is_equal(4)

	# Empathy should be psyche + 1
	assert_int(_character_stats.empathy).is_equal(3)

	# Authority should be psyche + physique
	assert_int(_character_stats.authority).is_equal(4)


func test_modify_attribute_updates_skills():
	"""Test that modifying attributes updates dependent skills"""
	var initial_logic = _character_stats.logic

	_character_stats.modify_attribute("intellect", 2)

	# Intellect should increase from 2 to 4
	assert_int(_character_stats.intellect).is_equal(4)

	# Logic should increase by 2 (was intellect + 1)
	assert_int(_character_stats.logic).is_equal(initial_logic + 2)


func test_modify_attribute_minimum_value():
	"""Test that attributes don't go below 1"""
	_character_stats.modify_attribute("intellect", -10)

	# Should clamp to minimum of 1
	assert_int(_character_stats.intellect).is_equal(1)


func test_skill_check_returns_result_dictionary():
	"""Test that skill check returns properly formatted result"""
	var result = _character_stats.perform_skill_check("logic", 10)

	# Verify result dictionary has expected keys
	assert_that(result).contains_keys(
		["skill", "skill_value", "roll", "total", "difficulty", "success", "margin"]
	)

	# Verify skill name is correct
	assert_str(result.skill).is_equal("logic")

	# Verify difficulty is set correctly
	assert_int(result.difficulty).is_equal(10)

	# Roll should be between 2 and 12 (2d6)
	assert_int(result.roll).is_between(2, 12)


func test_skill_check_success_calculation():
	"""Test that skill check success is determined correctly"""
	# Set up character with high intellect for better odds
	_character_stats.modify_attribute("intellect", 10)

	# Perform multiple checks to verify calculation
	var result = _character_stats.perform_skill_check("logic", 5)

	# Total should be skill_value + roll
	assert_int(result.total).is_equal(result.skill_value + result.roll)

	# Success should be true if total >= difficulty
	if result.total >= result.difficulty:
		assert_bool(result.success).is_true()
	else:
		assert_bool(result.success).is_false()


func test_get_skill_value_returns_correct_values():
	"""Test that get_skill_value returns correct values for all skills"""
	assert_int(_character_stats.get_skill_value("logic")).is_equal(3)
	assert_int(_character_stats.get_skill_value("rhetoric")).is_equal(4)
	assert_int(_character_stats.get_skill_value("empathy")).is_equal(3)
	assert_int(_character_stats.get_skill_value("authority")).is_equal(4)


func test_get_skill_value_returns_default_for_unknown():
	"""Test that unknown skills return default value of 1"""
	assert_int(_character_stats.get_skill_value("unknown_skill")).is_equal(1)


func test_health_modification():
	"""Test health modification and clamping"""
	# Initial health should be 100
	assert_int(_character_stats.health).is_equal(100)

	# Reduce health
	_character_stats.modify_health(-30)
	assert_int(_character_stats.health).is_equal(70)

	# Health should clamp at 0
	_character_stats.modify_health(-100)
	assert_int(_character_stats.health).is_equal(0)

	# Heal back up
	_character_stats.modify_health(50)
	assert_int(_character_stats.health).is_equal(50)

	# Health should clamp at 100
	_character_stats.modify_health(100)
	assert_int(_character_stats.health).is_equal(100)


func test_morale_modification():
	"""Test morale modification and clamping"""
	# Initial morale should be 100
	assert_int(_character_stats.morale).is_equal(100)

	# Reduce morale
	_character_stats.modify_morale(-40)
	assert_int(_character_stats.morale).is_equal(60)

	# Morale should clamp at 0
	_character_stats.modify_morale(-100)
	assert_int(_character_stats.morale).is_equal(0)

	# Increase morale
	_character_stats.modify_morale(30)
	assert_int(_character_stats.morale).is_equal(30)

	# Morale should clamp at 100
	_character_stats.modify_morale(100)
	assert_int(_character_stats.morale).is_equal(100)
