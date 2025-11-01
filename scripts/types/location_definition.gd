class_name LocationDefinition
extends Resource

## Self-documenting location definition
## Describes a complete game location/scene

@export var location_id: String  ## Unique identifier
@export var display_name: String  ## Human-readable name
@export var description: String  ## What this location is (for agents)

## Visual assets
@export var background_texture: Texture2D  ## Main background image
@export var foreground_texture: Texture2D  ## Elements that render above player (doorframes, etc.)

## Spatial data
@export var scene_bounds: Rect2 = Rect2(0, 0, 1920, 1080)  ## Scene dimensions
## Polygons defining where player can walk
@export var walkable_areas: Array[PackedVector2Array] = []

## Content
@export var npc_placements: Array[NPCPlacement] = []  ## Which NPCs are here and where
@export var trigger_zones: Array[TriggerZone] = []  ## Story triggers, music changes, etc.

## Story integration
@export var required_flags: Array[String] = []  ## Flags needed to access this location
@export var sets_flags: Array[String] = []  ## Flags set when entering this location
@export var music_state: String = "ambient"  ## Music state for this location


func _to_string() -> String:
	return (
		"Location[id=%s, name=%s, npcs=%d, triggers=%d]"
		% [location_id, display_name, npc_placements.size(), trigger_zones.size()]
	)


## Helper: Get all NPC IDs in this location
func get_npc_ids() -> Array[String]:
	var ids: Array[String] = []
	for placement in npc_placements:
		ids.append(placement.npc_id)
	return ids


## Helper: Check if location is accessible given current flags
func is_accessible(current_flags: Dictionary) -> bool:
	for flag in required_flags:
		if not current_flags.get(flag, false):
			return false
	return true
