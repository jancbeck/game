extends GdUnitTestSuite


## Smoke test: Verify CombatManager autoload exists
func test_combat_manager_exists() -> void:
	var combat_manager := CombatManager

	assert_object(combat_manager).is_not_null()


## Smoke test: Verify CombatManager has required signals
func test_combat_manager_signals() -> void:
	var combat_manager := CombatManager

	assert_bool(combat_manager.has_signal("attack_landed")).is_true()
	assert_bool(combat_manager.has_signal("damage_dealt")).is_true()
	assert_bool(combat_manager.has_signal("fighter_defeated")).is_true()


## Smoke test: Verify CombatManager has helper methods
func test_combat_manager_methods() -> void:
	var combat_manager := CombatManager

	assert_bool(combat_manager.has_method("is_in_attack_range")).is_true()
	assert_bool(combat_manager.has_method("apply_damage")).is_true()
	assert_bool(combat_manager.has_method("process_hitbox_collision")).is_true()
