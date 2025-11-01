class_name ScreenshotManagerIntegrationTest
extends GdUnitTestSuite

## Integration test for ScreenshotManager
## Tests actual screenshot capture with a viewport

var _screenshot_manager: Node
var _temp_screenshots_folder: String = "test_screenshots_integration"
var _viewport: SubViewport


func before_test():
	"""Initialize test environment with a viewport"""
	# Create a viewport for testing
	_viewport = auto_free(SubViewport.new())
	_viewport.size = Vector2i(320, 240)
	_viewport.transparent_bg = false

	# Add a simple visual element to the viewport
	var color_rect := ColorRect.new()
	color_rect.size = Vector2(320, 240)
	color_rect.color = Color(0.2, 0.5, 0.8)  # Blue color for testing
	_viewport.add_child(color_rect)

	# Create screenshot manager
	_screenshot_manager = auto_free(load("res://scripts/screenshot_manager.gd").new())
	_screenshot_manager.screenshots_folder = _temp_screenshots_folder
	_screenshot_manager.enable_keyboard_shortcut = false

	# Add to the scene tree
	add_child(_viewport)
	_viewport.add_child(_screenshot_manager)

	# Create temporary screenshots folder
	var dir := DirAccess.open("res://")
	if dir and not dir.dir_exists(_temp_screenshots_folder):
		dir.make_dir(_temp_screenshots_folder)

	# Wait for viewport to render
	await get_tree().process_frame
	await get_tree().process_frame


func after_test():
	"""Clean up after test"""
	# Clean up test screenshots
	var dir := DirAccess.open("res://" + _temp_screenshots_folder)
	if dir:
		dir.list_dir_begin()
		var file_name := dir.get_next()
		while file_name != "":
			if not dir.current_is_dir():
				dir.remove(file_name)
			file_name = dir.get_next()
		dir.list_dir_end()

	# Remove folder
	var root_dir := DirAccess.open("res://")
	if root_dir:
		root_dir.remove(_temp_screenshots_folder)


func test_take_screenshot_creates_file():
	"""Test that taking a screenshot actually creates a file"""
	var custom_name: String = "integration_test_screenshot"
	var filepath: String = _screenshot_manager.take_screenshot(custom_name)

	# In headless mode, screenshots may fail - this is expected
	# We test that the function returns appropriately
	if DisplayServer.get_name() == "headless":
		# In headless mode, screenshot should fail gracefully
		assert_str(filepath).is_empty()
	else:
		# Verify filepath is not empty
		assert_str(filepath).is_not_empty()

		# Verify file was created
		assert_bool(FileAccess.file_exists("res://" + filepath)).is_true()

		# Verify file has content (PNG should be at least 100 bytes)
		var file := FileAccess.open("res://" + filepath, FileAccess.READ)
		if file:
			var file_size := file.get_length()
			file.close()
			assert_int(file_size).is_greater(100)


func test_screenshot_signal_emission():
	"""Test that screenshot_taken signal is emitted"""
	var signal_emitted := false
	var emitted_filepath: String = ""

	_screenshot_manager.screenshot_taken.connect(
		func(filepath: String):
			signal_emitted = true
			emitted_filepath = filepath
	)

	var custom_name: String = "signal_test_screenshot"
	var filepath: String = _screenshot_manager.take_screenshot(custom_name)

	# Wait for signal processing
	await get_tree().process_frame

	# In headless mode, signal won't emit due to no rendering context
	if DisplayServer.get_name() == "headless":
		assert_bool(signal_emitted).is_false()
	else:
		assert_bool(signal_emitted).is_true()
		assert_str(emitted_filepath).is_equal(filepath)


func test_multiple_screenshots_unique_names():
	"""Test that multiple screenshots get unique filenames"""
	var filepath1: String = _screenshot_manager.take_screenshot()
	await get_tree().process_frame

	var filepath2: String = _screenshot_manager.take_screenshot()

	# In headless mode, this test is skipped as screenshots won't work
	if DisplayServer.get_name() != "headless":
		# Verify both files were created
		assert_bool(FileAccess.file_exists("res://" + filepath1)).is_true()
		assert_bool(FileAccess.file_exists("res://" + filepath2)).is_true()

		# Verify filenames are different
		assert_str(filepath1).is_not_equal(filepath2)
	else:
		# In headless mode, both should return empty strings
		assert_str(filepath1).is_empty()
		assert_str(filepath2).is_empty()
