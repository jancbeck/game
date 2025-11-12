extends GdUnitTestSuite


# Smoke test: Verify PlayerState starts with default fire_cooldown
func test_playerstate_default_fire_cooldown() -> void:
	PlayerState.reset()
	assert_float(PlayerState.fire_cooldown).is_equal(0.18)


# Smoke test: Verify apply_boon reduces fire_cooldown
func test_playerstate_apply_boon() -> void:
	PlayerState.reset()
	var initial_cooldown: float = PlayerState.fire_cooldown
	PlayerState.apply_boon()

	assert_float(PlayerState.fire_cooldown).is_equal(initial_cooldown * 0.65)


# Smoke test: Verify is_max_fire_rate at minimum
func test_playerstate_is_max_fire_rate() -> void:
	PlayerState.reset()
	PlayerState.fire_cooldown = PlayerState.MIN_FIRE_COOLDOWN

	assert_bool(PlayerState.is_max_fire_rate()).is_true()


# Smoke test: Verify reset restores default fire_cooldown
func test_playerstate_reset() -> void:
	PlayerState.fire_cooldown = 0.05
	PlayerState.reset()

	assert_float(PlayerState.fire_cooldown).is_equal(0.18)
