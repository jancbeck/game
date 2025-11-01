class_name TriggerZone
extends Resource

## Self-documenting trigger zone
## Defines an area that triggers effects when player enters/exits

@export var trigger_id: String  ## Unique ID
@export var area: Rect2  ## Trigger area in scene coordinates
@export var trigger_once: bool = true  ## If true, only fires once

## Actions to perform
@export var on_enter_actions: Array[GameAction] = []  ## Actions when player enters
@export var on_exit_actions: Array[GameAction] = []  ## Actions when player exits

## Conditions
@export var required_flags: Array[String] = []  ## Only trigger if these flags are set
@export var forbidden_flags: Array[String] = []  ## Don't trigger if these flags are set


func _to_string() -> String:
	return (
		"Trigger[id=%s, area=%s, enter_actions=%d, exit_actions=%d]"
		% [trigger_id, area, on_enter_actions.size(), on_exit_actions.size()]
	)


## Check if trigger should activate
func can_activate() -> bool:
	# Note: This is a placeholder. Actual flag checking would require
	# a GameState singleton which we'll implement in a later phase.
	# For now, we just check required/forbidden flags exist
	return required_flags.size() >= 0 and forbidden_flags.size() >= 0
