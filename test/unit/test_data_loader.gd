# tests/unit/test_data_loader.gd
extends GdUnitTestSuite


func test_get_quest_returns_data_from_file():
	# Arrange
	var expected_data = {
		"id": "rescue_prisoner",
		"act": 2,
		"prerequisites": ["joined_rebels"],
		"approaches":
		{
			"violent":
			{
				"requires": {"violence_thoughts": 3},
				"degrades": {"flexibility_charisma": -2},
				"rewards":
				{
					"convictions": {"violence_thoughts": 2},
					"memory_flags": ["guard_captain_hostile", "reputation_brutal"]
				}
			},
			"stealthy":
			{
				"requires": {"flexibility_cunning": 5},
				"degrades": {"flexibility_cunning": -1},
				"rewards":
				{"convictions": {"deceptive_acts": 2}, "memory_flags": ["guard_captain_unaware"]}
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
	# Check specific fields to avoid test fragility with full dict matching if parser adds extra fields
	assert_that(quest_data["id"]).is_equal(expected_data["id"])
	assert_that(quest_data["act"]).is_equal(expected_data["act"])
	assert_that(quest_data["approaches"]["violent"]["requires"]).is_equal(
		expected_data["approaches"]["violent"]["requires"]
	)
	assert_that(quest_data["approaches"]["stealthy"]["degrades"]).is_equal(
		expected_data["approaches"]["stealthy"]["degrades"]
	)
	assert_that(quest_data["outcomes"]["all"]).is_equal(expected_data["outcomes"]["all"])


func test_get_quest_returns_empty_dictionary_for_unknown_quest():
	# Act
	var quest_data = DataLoader.get_quest("unknown_quest")

	# Assert
	assert_that(quest_data).is_equal({})
