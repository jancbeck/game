class_name DataLoader
extends RefCounted

## Manages loading and parsing of all game data files.
## This includes quests, dialogues, characters, items, and world data.
## All functions are static and operate on file paths to load data.

## Example:
##   var quest_data = DataLoader.get_quest("rescue_prisoner")


# Placeholder for now, will be replaced with actual file loading
static func get_quest(quest_id: String) -> Dictionary:
	# In a real scenario, this would load from data/quests/{quest_id}.md
	# For now, return a dummy quest to unblock QuestSystem development.
	if quest_id == "rescue_prisoner":
		return {
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
				[
					{"advance_to": "report_to_rebel_leader"},
					{"unlock_location": "rebel_hideout_innere"}
				]
			}
		}

	if quest_id == "report_to_rebel_leader":
		return {
			"id": "report_to_rebel_leader",
			"act": 1,
			"location": "rebel_hideout",
			"prerequisites": [{"completed": "rescue_prisoner"}],
			"approaches": {},
			"outcomes": {}
		}

	return {}
