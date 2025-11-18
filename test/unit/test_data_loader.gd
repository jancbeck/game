# tests/unit/test_data_loader.gd
extends GdUnitTestSuite


func test_get_quest_returns_dummy_data_for_rescue_prisoner():
	# Arrange
	var expected_data = {
		"id": "rescue_prisoner",
		"act": 1,
		"location": "king_dungeons",
		"prerequisites": [{"completed": "joined_rebels"}],
		"approaches":
		{
			"violent":
			{
				"label": "Fight guards",
				"requires": {"violence_thoughts": 3},
				"degrades": {"flexibility_charisma": -2},
				"rewards":
				{"convictions": {"violence_thoughts": 2}, "memory_flags": ["guard_hostile"]}
			},
			"stealthy":
			{
				"label": "Use sewers",
				"requires": {"flexibility_cunning": 5},
				"degrades": {"flexibility_cunning": -1},
				"rewards": {"convictions": {"cunning": 1}, "memory_flags": ["guard_unaware"]}
			}
		},
		"outcomes":
		{
			"all":
			[{"advance_to": "report_to_rebel_leader"}, {"unlock_location": "rebel_hideout_innere"}]
		}
	}

	# Act
	var quest_data = DataLoader.get_quest("rescue_prisoner")

	# Assert
	assert_that(quest_data).is_equal(expected_data)


func test_get_quest_returns_empty_dictionary_for_unknown_quest():
	# Act
	var quest_data = DataLoader.get_quest("unknown_quest")

	# Assert
	assert_that(quest_data).is_equal({})
