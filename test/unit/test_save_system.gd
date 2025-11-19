extends GdUnitTestSuite

const SaveSystemScript = preload("res://scripts/core/save_system.gd")

var _temp_state = {
	"player": {"health": 50, "position": Vector3(10, 5, 2)},
	"world": {"act": 2}
}

func after_each():
	# Clean up save file
	if FileAccess.file_exists(SaveSystem.SAVE_PATH):
		DirAccess.remove_absolute(SaveSystem.SAVE_PATH)

func test_save_and_load():
	# Act
	SaveSystem.save_state(_temp_state)
	var loaded = SaveSystem.load_state()
	
	# Assert
	assert_that(loaded["player"]["health"]).is_equal(50)
	assert_that(loaded["world"]["act"]).is_equal(2)
	# Vector3 should be preserved exactly as Vector3 type, not String
	assert_that(loaded["player"]["position"]).is_equal(Vector3(10, 5, 2))
	assert_that(typeof(loaded["player"]["position"])).is_equal(TYPE_VECTOR3)

func test_load_non_existent_returns_empty():
	if FileAccess.file_exists(SaveSystem.SAVE_PATH):
		DirAccess.remove_absolute(SaveSystemScript.SAVE_PATH)
		
	var loaded = SaveSystemScript.load_state()
	assert_that(loaded).is_empty()