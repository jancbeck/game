extends GdUnitTestSuite


# Smoke test: Verify Bullet initializes with correct damage value
func test_bullet_has_correct_damage() -> void:
	var bullet_scene: PackedScene = load("res://src/items/bullet/Bullet.tscn")
	var bullet: Area2D = auto_free(bullet_scene.instantiate())

	assert_int(bullet.damage).is_equal(20)


# Smoke test: Verify Bullet has default speed


func test_bullet_speed() -> void:
	var bullet_scene: PackedScene = load("res://src/items/bullet/Bullet.tscn")
	var bullet: Area2D = auto_free(bullet_scene.instantiate())

	assert_float(bullet.speed).is_equal(900.0)


# Smoke test: Verify Bullet can be instantiated


func test_bullet_instantiation() -> void:
	var bullet_scene: PackedScene = load("res://src/items/bullet/Bullet.tscn")
	var bullet: Area2D = auto_free(bullet_scene.instantiate())

	assert_object(bullet).is_not_null()
	assert_bool(bullet is Area2D).is_true()
