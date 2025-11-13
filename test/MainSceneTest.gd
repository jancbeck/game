extends GdUnitTestSuite


## Smoke test: Verify main scene loads
func test_main_scene_loads() -> void:
	var main_scene: PackedScene = load("res://src/core/main.tscn")
	var main: Node3D = auto_free(main_scene.instantiate())
	add_child(main)

	await get_tree().process_frame

	assert_object(main).is_not_null()


## Smoke test: Verify Camera3D exists
func test_camera_exists() -> void:
	var main_scene: PackedScene = load(MAIN_SCENE)
	var main: Node3D = auto_free(main_scene.instantiate())
	add_child(main)

	await get_tree().process_frame

	var camera := main.get_node("Camera3D")
	assert_object(camera).is_not_null()
	assert_bool(camera is Camera3D).is_true()


## Smoke test: Verify DirectionalLight3D has shadows enabled
func test_directional_light_shadows() -> void:
	var main_scene: PackedScene = load(MAIN_SCENE)
	var main: Node3D = auto_free(main_scene.instantiate())
	add_child(main)

	await get_tree().process_frame

	var light := main.get_node("DirectionalLight3D") as DirectionalLight3D
	assert_object(light).is_not_null()
	assert_bool(light.shadow_enabled).is_true()


## Smoke test: Verify spawn markers exist
func test_spawn_markers_exist() -> void:
	var main_scene: PackedScene = load(MAIN_SCENE)
	var main: Node3D = auto_free(main_scene.instantiate())
	add_child(main)

	await get_tree().process_frame

	assert_object(main.get_node("FighterSpawn1")).is_not_null()
	assert_object(main.get_node("FighterSpawn2")).is_not_null()
