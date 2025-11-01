class_name ScreenshotManagerTest
extends GdUnitTestSuite

## Unit test for ScreenshotManager
## Tests screenshot capture and file management functionality

var _screenshot_manager: Node
var _temp_screenshots_folder: String = "test_screenshots"


func before_test():
	"""Initialize test data before each test case"""
	_screenshot_manager = auto_free(load("res://scripts/screenshot_manager.gd").new())
	_screenshot_manager.screenshots_folder = _temp_screenshots_folder
	_screenshot_manager.enable_keyboard_shortcut = false

	# Create temporary screenshots folder
	var dir := DirAccess.open("res://")
	if dir and not dir.dir_exists(_temp_screenshots_folder):
		dir.make_dir(_temp_screenshots_folder)


func after_test():
	"""Clean up after each test"""
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


func test_screenshot_manager_initializes():
	"""Test that screenshot manager initializes correctly"""
	assert_object(_screenshot_manager).is_not_null()
	assert_str(_screenshot_manager.screenshots_folder).is_equal(_temp_screenshots_folder)


func test_generate_filename_with_custom_name():
	"""Test that custom filename is generated correctly"""
	var custom_name: String = "test_screenshot"
	var filename: String = _screenshot_manager._generate_filename(custom_name)

	assert_str(filename).is_equal("test_screenshot.png")


func test_generate_filename_with_timestamp():
	"""Test that timestamp-based filename is generated correctly"""
	var filename: String = _screenshot_manager._generate_filename()

	# Should contain "screenshot_" prefix and ".png" extension
	assert_str(filename).contains("screenshot_")
	assert_str(filename).ends_with(".png")

	# Should contain date format YYYY-MM-DD
	assert_str(filename).contains("-")


func test_screenshot_counter_increments():
	"""Test that screenshot counter increments with each screenshot"""
	var initial_counter: int = _screenshot_manager.screenshot_counter

	_screenshot_manager._generate_filename()
	assert_int(_screenshot_manager.screenshot_counter).is_equal(initial_counter + 1)

	_screenshot_manager._generate_filename()
	assert_int(_screenshot_manager.screenshot_counter).is_equal(initial_counter + 2)


func test_screenshots_folder_path():
	"""Test that screenshots folder path is set correctly"""
	assert_str(_screenshot_manager.screenshots_folder).is_equal(_temp_screenshots_folder)
