extends GdUnitTestSuite


# Integration test: Verify Room spawns player
func test_room_spawns_player() -> void:
	var room_scene: PackedScene = load("res://src/world/room/Room.tscn")
	var room: Node2D = auto_free(room_scene.instantiate())
	add_child(room)

	await get_tree().process_frame

	var players := get_tree().get_nodes_in_group("player")
	assert_int(players.size()).is_equal(1)


# Integration test: Verify Room spawns correct number of enemies


func test_room_spawns_enemies() -> void:
	var room_scene: PackedScene = load("res://src/world/room/Room.tscn")
	var room: Node2D = auto_free(room_scene.instantiate())
	add_child(room)

	await get_tree().process_frame

	var enemies := get_tree().get_nodes_in_group("enemies")
	assert_int(enemies.size()).is_equal(3)


# Integration test: Verify Room has playable area defined
func test_room_has_playable_area() -> void:
	var room_scene: PackedScene = load("res://src/world/room/Room.tscn")
	var room: Node2D = auto_free(room_scene.instantiate())
	add_child(room)

	await get_tree().process_frame

	assert_object(room.playable_area).is_not_null()
	assert_float(room.playable_area.size.x).is_greater(0.0)
	assert_float(room.playable_area.size.y).is_greater(0.0)


# Integration test: Verify Room has exit area
func test_room_has_exit() -> void:
	var room_scene: PackedScene = load("res://src/world/room/Room.tscn")
	var room: Node2D = auto_free(room_scene.instantiate())
	add_child(room)

	await get_tree().process_frame

	var exit := room.get_node("Exit")
	assert_object(exit).is_not_null()
