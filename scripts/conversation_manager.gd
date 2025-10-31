extends Node

const UI_SCENE := preload("res://scenes/ui/ConversationUI.tscn")

var conversation_ui : CanvasLayer
var current_conversation : Dictionary
var current_node_key : String = ""
var current_npc : Node
var player : Node

func _ready() -> void:
    conversation_ui = UI_SCENE.instantiate()
    conversation_ui.set_manager(self)
    get_tree().root.add_child(conversation_ui)

func start_conversation(conversation : Dictionary, npc_ref : Node, player_ref : Node) -> void:
    if conversation.is_empty():
        return
    current_conversation = conversation
    current_node_key = conversation.get("start", conversation.keys()[0])
    current_npc = npc_ref
    player = player_ref
    _show_current_node()

func _show_current_node() -> void:
    if not current_conversation.has(current_node_key):
        _end_conversation()
        return
    var node_data : Dictionary = current_conversation[current_node_key]
    if node_data.get("end", false):
        _end_conversation()
        return
    var processed_data := _process_node(node_data)
    conversation_ui.show_line(processed_data)

func _process_node(node_data : Dictionary) -> Dictionary:
    var copy := node_data.duplicate(true)
    var options : Array = []
    for option in copy.get("options", []):
        var new_option := option.duplicate(true)
        if option.has("skill_check"):
            var check : Dictionary = option["skill_check"]
            var skill : String = check.get("skill", "")
            var difficulty : int = check.get("difficulty", 10)
            var result := _preview_skill_check(skill, difficulty)
            new_option["text"] = "%s\n%s" % [option.get("text", ""), result]
        options.append(new_option)
    copy["options"] = options
    var voice := WorldState.get_internal_voice(copy.get("voice_skill", ""))
    if voice and voice != "":
        copy["text"] = "[b]%s whispers:[/b] %s\n\n%s" % [voice, copy.get("voice_text", ""), copy.get("text", "")]
    return copy

func _preview_skill_check(skill : String, difficulty : int) -> String:
    if not WorldState.stats.has(skill):
        return "[color=gray](Unknown skill)[/color]"
    var stat_value : int = WorldState.stats[skill]
    var chance := clamp(0.15 + float(stat_value) / (difficulty * 1.2), 0.05, 0.95)
    return "[color=skyblue][%s %d • %d%%][/color]" % [skill.capitalize(), difficulty, int(chance * 100.0)]

func _perform_skill_check(skill : String, difficulty : int) -> bool:
    var stat_value : int = WorldState.stats.get(skill, 0)
    var roll := randi_range(1, 20)
    return stat_value + roll >= difficulty

func _on_option_selected(option : Dictionary) -> void:
    if option.has("skill_check"):
        var check : Dictionary = option["skill_check"]
        var success := _perform_skill_check(check.get("skill", ""), check.get("difficulty", 10))
        var next_key := success ? check.get("success_next", "") : check.get("failure_next", "")
        _apply_option_effects(option, success)
        if next_key == "":
            _end_conversation()
            return
        current_node_key = next_key
        _show_current_node()
        return
    _apply_option_effects(option, true)
    var next_state : String = option.get("next", "")
    if next_state == "":
        _end_conversation()
        return
    current_node_key = next_state
    _show_current_node()

func _apply_option_effects(option : Dictionary, success : bool) -> void:
    if option.has("notebook_entry"):
        WorldState.add_notebook_entry(option["notebook_entry"])
    if option.has("faction_delta"):
        for faction_name in option["faction_delta"].keys():
            var delta : int = option["faction_delta"][faction_name]
            WorldState.adjust_faction(faction_name, delta)
    if option.has("advance_time") and option["advance_time"]:
        WorldState.advance_time(1)
    if option.has("on_success") and success:
        option["on_success"].call_deferred()
    if option.has("on_failure") and not success:
        option["on_failure"].call_deferred()

func _on_continue_pressed() -> void:
    var node_data : Dictionary = current_conversation.get(current_node_key, {})
    var next_state : String = node_data.get("next", "")
    if next_state == "":
        _end_conversation()
        return
    current_node_key = next_state
    _show_current_node()

func _end_conversation() -> void:
    conversation_ui.hide_ui()
    current_conversation.clear()
    current_node_key = ""
    if current_npc:
        current_npc.on_conversation_finished()
    current_npc = null
    player = null
