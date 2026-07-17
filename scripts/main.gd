extends Node3D
## Game controller: connects the world (player, NPCs) to the dialogue UI
## and the store. Owns the currently running DialogueRunner.

var runner: DialogueRunner = null
var nearby_npc: Npc = null

@onready var player: Player = $Player
@onready var dialogue_ui: Control = $UI/DialogueUI
@onready var hud: Control = $UI/Hud


func _ready() -> void:
	for npc: Npc in get_tree().get_nodes_in_group("npcs"):
		npc.player_entered.connect(_on_npc_in_range)
		npc.player_exited.connect(_on_npc_out_of_range)
	dialogue_ui.option_chosen.connect(_on_option_chosen)
	Store.state_changed.connect(func(_s: Dictionary) -> void: hud.refresh())
	hud.refresh()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("interact") and runner == null and nearby_npc != null:
		start_dialogue(nearby_npc)
	elif event.is_action_pressed("save_game"):
		SaveSystem.save_game(Store.get_state())
		hud.flash_message("Game saved")
	elif event.is_action_pressed("load_game"):
		var loaded := SaveSystem.load_game()
		if loaded.is_empty():
			hud.flash_message("No save found")
		elif Store.restore(loaded):
			hud.flash_message("Game loaded")


func start_dialogue(npc: Npc) -> void:
	var data: Dictionary = Db.get_dialogue(npc.dialogue_id)
	if data.is_empty():
		return
	npc.face(player.global_position)
	runner = DialogueRunner.new(data)
	runner.ended.connect(_on_dialogue_ended)
	runner.start()
	player.input_enabled = false
	_show_current_node(npc.npc_name)


func _show_current_node(speaker_fallback: String) -> void:
	var node := runner.current_node()
	var speaker: String = node.get("speaker", speaker_fallback)
	dialogue_ui.show_node(speaker, node.get("text", ""), runner.visible_options(Store.get_state()))


func _on_option_chosen(option_index: int) -> void:
	if runner == null:
		return
	runner.choose(option_index, Store)
	if runner != null and runner.is_running():
		_show_current_node(nearby_npc.npc_name if nearby_npc else "")


func _on_dialogue_ended() -> void:
	runner = null
	dialogue_ui.hide()
	player.input_enabled = true


func _on_npc_in_range(npc: Npc) -> void:
	nearby_npc = npc
	hud.show_prompt("[E] Talk to %s" % npc.npc_name)


func _on_npc_out_of_range(npc: Npc) -> void:
	if nearby_npc == npc:
		nearby_npc = null
		hud.hide_prompt()
