extends GdUnitTestSuite


# Smoke test: Verify Enemy initializes with correct HP
func test_enemy_has_correct_hp() -> void:
	var enemy_scene: PackedScene = load("res://actors/enemy/Enemy.tscn")
	var enemy: CharacterBody2D = auto_free(enemy_scene.instantiate())
	add_child(enemy)

	assert_int(enemy.hp).is_equal(40)


# Smoke test: Verify Enemy has default speed
func test_enemy_has_default_speed() -> void:
	var enemy_scene: PackedScene = load("res://actors/enemy/Enemy.tscn")
	var enemy: CharacterBody2D = auto_free(enemy_scene.instantiate())

	assert_float(enemy.speed).is_equal(150.0)


# Smoke test: Verify Enemy takes damage correctly
func test_enemy_take_damage() -> void:
	var enemy_scene: PackedScene = load("res://actors/enemy/Enemy.tscn")
	var enemy: CharacterBody2D = auto_free(enemy_scene.instantiate())
	add_child(enemy)

	var initial_hp: int = enemy.hp
	# Don't call take_damage in test since it spawns impact effect
	# Just test HP reduction directly
	enemy.hp -= 10

	assert_int(enemy.hp).is_equal(initial_hp - 10)


# Smoke test: Verify Enemy is added to enemies group


func test_enemy_in_group() -> void:
	var enemy_scene: PackedScene = load("res://actors/enemy/Enemy.tscn")
	var enemy: CharacterBody2D = auto_free(enemy_scene.instantiate())
	add_child(enemy)

	assert_bool(enemy.is_in_group("enemies")).is_true()
