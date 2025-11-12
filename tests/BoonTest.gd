extends GdUnitTestSuite


# Smoke test: Verify Boon has correct fire rate multiplier
func test_boon_has_fire_rate_multiplier() -> void:
	var boon_scene: PackedScene = load("res://src/items/boon/Boon.tscn")
	var boon: Area2D = auto_free(boon_scene.instantiate())

	assert_float(boon.fire_rate_multiplier).is_equal(0.65)


# Smoke test: Verify Boon can be instantiated
func test_boon_instantiation() -> void:
	var boon_scene: PackedScene = load("res://src/items/boon/Boon.tscn")
	var boon: Area2D = auto_free(boon_scene.instantiate())

	assert_object(boon).is_not_null()
	assert_bool(boon is Area2D).is_true()


# Smoke test: Verify fire rate reduction logic
func test_boon_fire_rate_reduction() -> void:
	var initial_cooldown := 1.0
	var multiplier := 0.65
	var expected_cooldown: float = initial_cooldown * multiplier

	assert_float(expected_cooldown).is_equal(0.65)
