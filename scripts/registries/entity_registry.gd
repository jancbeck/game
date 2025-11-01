class_name EntityRegistry
extends Node

## Central registry of all game entities
## Provides type-safe access to entity definitions
## Agents can query this to see all available entities

# Note: These will be populated as we create actual entity resources
# For now, we provide the structure with empty dictionaries
const NPCS: Dictionary = {
# Example: "test_npc": preload("res://data/entities/npcs/test_npc.tres"),
# More NPCs added here
}

const ITEMS: Dictionary = {
# Items will go here
}

const LOCATIONS: Dictionary = {
# Example: "main": preload("res://data/locations/main.tres"),
# More locations added here
}


static func get_npc(npc_id: String) -> NPCDefinition:
	assert(NPCS.has(npc_id), "Unknown NPC: %s. Available: %s" % [npc_id, NPCS.keys()])
	return NPCS[npc_id]


static func get_location(location_id: String) -> LocationDefinition:
	assert(
		LOCATIONS.has(location_id),
		"Unknown location: %s. Available: %s" % [location_id, LOCATIONS.keys()]
	)
	return LOCATIONS[location_id]


static func get_all_npc_ids() -> Array[String]:
	var ids: Array[String] = []
	ids.assign(NPCS.keys())
	return ids


static func get_all_location_ids() -> Array[String]:
	var ids: Array[String] = []
	ids.assign(LOCATIONS.keys())
	return ids


static func has_npc(npc_id: String) -> bool:
	return NPCS.has(npc_id)


static func has_location(location_id: String) -> bool:
	return LOCATIONS.has(location_id)
