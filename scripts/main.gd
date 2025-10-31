extends Node2D

const CHARACTER_SHEET_SCENE := preload("res://scenes/ui/CharacterSheet.tscn")
const NOTEBOOK_SCENE := preload("res://scenes/ui/NotebookUI.tscn")

@onready var player : Node = $World/Player
@onready var time_label : Label = $HUD/TimeLabel

var character_sheet : CanvasLayer
var notebook_ui : CanvasLayer

func _ready() -> void:
    character_sheet = CHARACTER_SHEET_SCENE.instantiate()
    notebook_ui = NOTEBOOK_SCENE.instantiate()
    add_child(character_sheet)
    add_child(notebook_ui)
    player.call("set_character_sheet", character_sheet)
    player.call("set_notebook_ui", notebook_ui)
    WorldState.connect("time_advanced", Callable(self, "_on_time_advanced"))
    _update_time_label()

func _on_time_advanced(_new_block : int) -> void:
    _update_time_label()

func _update_time_label() -> void:
    time_label.text = "Time: %s" % WorldState.describe_time_of_day()
