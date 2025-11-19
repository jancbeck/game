extends Node

## Bridge layer between Dialogic timelines and GameState reducers.
## Provides static methods that can be called from Dialogic events to trigger
## game logic while maintaining the pure reducer architecture.
## This autoload should be registered in project.godot.


## Starts a quest by dispatching to QuestSystem.start_quest
static func start_quest(quest_id: String) -> void:
	GameState.dispatch(func(state): return QuestSystem.start_quest(state, quest_id))


## Completes a quest with specified approach by dispatching to QuestSystem.complete_quest
static func complete_quest(quest_id: String, approach: String = "") -> void:
	GameState.dispatch(func(state): return QuestSystem.complete_quest(state, quest_id, approach))


## Modifies a conviction stat by dispatching to PlayerSystem.modify_conviction
static func modify_conviction(conviction_name: String, amount: int) -> void:
	GameState.dispatch(func(state): return PlayerSystem.modify_conviction(state, conviction_name, amount))


## Modifies a flexibility stat by dispatching to PlayerSystem.modify_flexibility
static func modify_flexibility(stat_name: String, amount: int) -> void:
	GameState.dispatch(func(state): return PlayerSystem.modify_flexibility(state, stat_name, amount))


## Checks if a quest can be started based on prerequisites
## Returns true if prerequisites are met, false otherwise
static func can_start_quest(quest_id: String) -> bool:
	return QuestSystem.can_start_quest(GameState.state, quest_id)


## Clears the active_thought meta flag
## Used when transitioning from JSON-based ThoughtSystem to Dialogic timelines
static func clear_active_thought() -> void:
	GameState.dispatch(func(state):
		var new_state = state.duplicate(true)
		if new_state.has("meta") and typeof(new_state["meta"]) == TYPE_DICTIONARY:
			new_state["meta"]["active_thought"] = ""
		return new_state
	)
