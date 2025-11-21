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


## Gets the current value of a flexibility stat
## Returns the stat value or 0 if not found
static func get_flexibility(stat_name: String) -> int:
	return GameState.state["player"]["flexibility"].get(stat_name, 0)


## Gets the current value of a conviction stat
## Returns the stat value or 0 if not found
static func get_conviction(conviction_name: String) -> int:
	return GameState.state["player"]["convictions"].get(conviction_name, 0)


## Checks if a memory flag exists in any NPC's memory_flags array
## Returns true if found, false otherwise
static func has_memory_flag(flag_name: String) -> bool:
	var npc_states = GameState.state.get("world", {}).get("npc_states", {})
	for npc_id in npc_states:
		if npc_states[npc_id].get("memory_flags", []).has(flag_name):
			return true
	return false



