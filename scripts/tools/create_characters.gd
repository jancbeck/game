@tool
extends EditorScript

func _run():
	# Guard Captain
	var guard = DialogicCharacter.new()
	guard.display_name = "Captain Varen"
	guard.color = Color(0.255, 0.412, 0.882, 1)  # Blue
	guard.custom_info = {"npc_id": "guard_captain"}
	ResourceSaver.save(guard, "res://data/characters/guard_captain.dch")
	print("Created: guard_captain.dch")

	# Rebel Leader
	var rebel = DialogicCharacter.new()
	rebel.display_name = "Elira"
	rebel.color = Color(0.863, 0.078, 0.235, 1)  # Red
	rebel.custom_info = {"npc_id": "rebel_leader"}
	ResourceSaver.save(rebel, "res://data/characters/rebel_leader.dch")
	print("Created: rebel_leader.dch")

	# Imprisoned Rebel
	var prisoner = DialogicCharacter.new()
	prisoner.display_name = "Imprisoned Rebel"
	prisoner.color = Color(0.502, 0.502, 0.502, 1)  # Gray
	prisoner.custom_info = {"npc_id": "imprisoned_rebel"}
	ResourceSaver.save(prisoner, "res://data/characters/imprisoned_rebel.dch")
	print("Created: imprisoned_rebel.dch")

	print("All characters created successfully")
