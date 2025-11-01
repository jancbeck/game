extends Node

## Screenshot Manager
## Provides functionality to capture and save screenshots of the game viewport.
## Useful for documentation, debugging, and visual feedback during development.

signal screenshot_taken(filepath: String)

@export var screenshots_folder: String = "screenshots"
@export var screenshot_key: Key = KEY_F12
@export var enable_keyboard_shortcut: bool = true

var screenshot_counter: int = 0


func _ready() -> void:
	# Create screenshots folder if it doesn't exist
	_ensure_screenshots_folder_exists()
	add_to_group("screenshot_manager")


func _ensure_screenshots_folder_exists() -> void:
	var dir := DirAccess.open("res://")
	if dir:
		if not dir.dir_exists(screenshots_folder):
			var error := dir.make_dir(screenshots_folder)
			if error != OK:
				push_error("Failed to create screenshots folder: " + str(error))
			else:
				print("Created screenshots folder at: res://" + screenshots_folder)


func _input(event: InputEvent) -> void:
	if not enable_keyboard_shortcut:
		return

	if event is InputEventKey:
		var key_event := event as InputEventKey
		if key_event.pressed and not key_event.echo and key_event.keycode == screenshot_key:
			take_screenshot()


## Takes a screenshot of the current viewport and saves it to the screenshots folder.
## Returns the filepath of the saved screenshot, or empty string if failed.
func take_screenshot(custom_name: String = "") -> String:
	var viewport := get_viewport()
	if not viewport:
		push_error("No viewport available for screenshot")
		return ""

	# Get the viewport texture and convert to image
	var image := viewport.get_texture().get_image()
	if not image:
		push_error("Failed to get image from viewport")
		return ""

	# Generate filename
	var filename := _generate_filename(custom_name)
	var filepath := screenshots_folder + "/" + filename

	# Save the image
	var error := image.save_png(filepath)
	if error != OK:
		push_error("Failed to save screenshot: " + str(error))
		return ""

	# Convert to absolute path for output
	var absolute_path := ProjectSettings.globalize_path("res://" + filepath)
	print("Screenshot saved: " + absolute_path)

	screenshot_taken.emit(filepath)
	return filepath


## Generates a filename for the screenshot based on timestamp or custom name
func _generate_filename(custom_name: String = "") -> String:
	if custom_name != "":
		return custom_name + ".png"

	# Use timestamp for unique filenames
	var datetime := Time.get_datetime_dict_from_system()
	var timestamp := (
		"%04d-%02d-%02d_%02d-%02d-%02d"
		% [
			datetime.year,
			datetime.month,
			datetime.day,
			datetime.hour,
			datetime.minute,
			datetime.second
		]
	)

	screenshot_counter += 1
	return "screenshot_%s_%03d.png" % [timestamp, screenshot_counter]


## Takes a screenshot after waiting for the specified number of frames.
## Useful for allowing the scene to fully render before capturing.
func take_screenshot_delayed(frames: int = 1, custom_name: String = "") -> String:
	for i in range(frames):
		await get_tree().process_frame
	return take_screenshot(custom_name)
