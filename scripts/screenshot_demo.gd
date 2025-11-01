extends Node2D

## Simple demo script to test screenshot functionality
## This script automatically takes a screenshot after a delay for testing purposes

@onready var screenshot_manager: Node = null


func _ready() -> void:
	# Find screenshot manager
	await get_tree().process_frame
	screenshot_manager = get_tree().get_first_node_in_group("screenshot_manager")

	if screenshot_manager:
		print("Screenshot Demo: ScreenshotManager found")
		print("Screenshot Demo: Press F12 to take a screenshot")
		print("Screenshot Demo: Screenshots will be saved to: res://screenshots/")

		# Connect to signal to get feedback
		screenshot_manager.screenshot_taken.connect(_on_screenshot_taken)
	else:
		print("Screenshot Demo: ERROR - ScreenshotManager not found!")


func _on_screenshot_taken(filepath: String) -> void:
	var absolute_path: String = ProjectSettings.globalize_path("res://" + filepath)
	print("Screenshot Demo: Screenshot captured!")
	print("Screenshot Demo: Saved to: " + absolute_path)

	# Add visual feedback in the game
	var label := Label.new()
	label.text = "Screenshot saved!\n" + filepath
	label.position = Vector2(20, 20)
	label.add_theme_color_override("font_color", Color.GREEN)
	add_child(label)

	# Remove label after 3 seconds
	await get_tree().create_timer(3.0).timeout
	if label and is_instance_valid(label):
		label.queue_free()
