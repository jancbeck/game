## Writes the pointer images, enlarged, to game/shots/cursor.png and cursor_hover.png.
##   Godot --headless --path game --script res://scripts/cursor_preview.gd
extends SceneTree

const Cursor := preload("res://scripts/cursor.gd")


func _initialize() -> void:
	Cursor.export_preview(ProjectSettings.globalize_path("res://shots"))
	quit()
