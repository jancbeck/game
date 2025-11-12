extends GdUnitTestSuite


# Smoke test: Verify Player has correct max_hp
func test_player_has_max_hp() -> void:
	var player_scene: PackedScene = load("res://actors/player/Player.tscn")
	var player: CharacterBody2D = auto_free(player_scene.instantiate())

	assert_int(player.max_hp).is_equal(100)


# Smoke test: Verify Player initializes with full hp
func test_player_starts_with_full_hp() -> void:
	var player_scene: PackedScene = load("res://actors/player/Player.tscn")
	var player: CharacterBody2D = auto_free(player_scene.instantiate())
	add_child(player)

	await get_tree().process_frame

	assert_int(player.hp).is_equal(player.max_hp)


# Smoke test: Verify take_damage reduces hp
func test_player_take_damage() -> void:
	var player_scene: PackedScene = load("res://actors/player/Player.tscn")
	var player: CharacterBody2D = auto_free(player_scene.instantiate())
	add_child(player)

	await get_tree().process_frame

	var initial_hp: int = player.hp
	player.take_damage(25)

	assert_int(player.hp).is_equal(initial_hp - 25)


# Smoke test: Verify Player is in player group
func test_player_in_group() -> void:
	var player_scene: PackedScene = load("res://actors/player/Player.tscn")
	var player: CharacterBody2D = auto_free(player_scene.instantiate())
	add_child(player)

	await get_tree().process_frame

	assert_bool(player.is_in_group("player")).is_true()
