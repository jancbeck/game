class_name GameAction
extends Resource

## Self-documenting game action
## Represents a side effect that can occur in the game
## Composable: multiple actions can be combined

enum ActionType {
	SET_FLAG,
	GIVE_ITEM,
	REMOVE_ITEM,
	START_DIALOGUE,
	CHANGE_MUSIC,
	SPAWN_NPC,
	DESPAWN_NPC,
	LOAD_LOCATION,
	PLAY_SFX,
}

@export var action_type: ActionType
@export var parameters: Dictionary = {}


func _to_string() -> String:
	return "GameAction[type=%s, params=%s]" % [ActionType.keys()[action_type], parameters]


## Execute this action
func execute() -> void:
	# Note: Actual execution will be implemented when we have the required
	# singletons (GameState, DialogueManager, AudioManager, SceneManager)
	# For now, we just provide the structure
	match action_type:
		ActionType.SET_FLAG:
			push_warning(
				(
					"SET_FLAG action: %s = %s (GameState not yet implemented)"
					% [parameters.get("flag", ""), parameters.get("value", true)]
				)
			)

		ActionType.GIVE_ITEM:
			push_warning(
				(
					"GIVE_ITEM action: %s (GameState not yet implemented)"
					% parameters.get("item_id", "")
				)
			)

		ActionType.REMOVE_ITEM:
			push_warning(
				(
					"REMOVE_ITEM action: %s (GameState not yet implemented)"
					% parameters.get("item_id", "")
				)
			)

		ActionType.START_DIALOGUE:
			push_warning(
				(
					"START_DIALOGUE action: %s (DialogueManager not yet implemented)"
					% parameters.get("dialogue_id", "")
				)
			)

		ActionType.CHANGE_MUSIC:
			push_warning(
				(
					"CHANGE_MUSIC action: %s (AudioManager not yet implemented)"
					% parameters.get("state", "ambient")
				)
			)

		ActionType.PLAY_SFX:
			push_warning(
				(
					"PLAY_SFX action: %s (AudioManager not yet implemented)"
					% parameters.get("sfx_path", "")
				)
			)

		ActionType.LOAD_LOCATION:
			push_warning(
				(
					"LOAD_LOCATION action: %s (SceneManager not yet implemented)"
					% parameters.get("location_id", "")
				)
			)

		_:
			push_warning("Unhandled action type: %s" % action_type)


## Factory methods for type-safe creation
static func set_flag(flag_name: String, value: bool = true) -> GameAction:
	var action := GameAction.new()
	action.action_type = ActionType.SET_FLAG
	action.parameters = {"flag": flag_name, "value": value}
	return action


static func give_item(item_id: String) -> GameAction:
	var action := GameAction.new()
	action.action_type = ActionType.GIVE_ITEM
	action.parameters = {"item_id": item_id}
	return action


static func start_dialogue(dialogue_id: String) -> GameAction:
	var action := GameAction.new()
	action.action_type = ActionType.START_DIALOGUE
	action.parameters = {"dialogue_id": dialogue_id}
	return action


static func change_music(state: String, fade_time: float = 2.0) -> GameAction:
	var action := GameAction.new()
	action.action_type = ActionType.CHANGE_MUSIC
	action.parameters = {"state": state, "fade_time": fade_time}
	return action
