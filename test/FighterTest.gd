extends GdUnitTestSuite


## Smoke test: Verify Fighter initializes with correct health
func test_fighter_has_correct_hp() -> void:
	var fighter_scene: PackedScene = load("res://src/characters/Fighter.tscn")
	var fighter: CharacterBody3D = auto_free(fighter_scene.instantiate())
	add_child(fighter)

	await get_tree().process_frame

	assert_int(fighter.hp).is_equal(100)


## Smoke test: Verify Fighter starts with full hp
func test_fighter_starts_with_full_hp() -> void:
	var fighter_scene: PackedScene = load(FIGHTER_SCENE)
	var fighter: CharacterBody3D = auto_free(fighter_scene.instantiate())
	add_child(fighter)

	await get_tree().process_frame

	assert_int(fighter.hp).is_equal(fighter.max_hp)


## Smoke test: Verify Fighter has AnimationTree
func test_fighter_has_animation_tree() -> void:
	var fighter_scene: PackedScene = load(FIGHTER_SCENE)
	var fighter: CharacterBody3D = auto_free(fighter_scene.instantiate())
	add_child(fighter)

	await get_tree().process_frame

	assert_object(fighter.get_node("AnimationTree")).is_not_null()
	assert_bool(fighter.get_node("AnimationTree") is AnimationTree).is_true()


## Smoke test: Verify Fighter is in fighters group
func test_fighter_in_group() -> void:
	var fighter_scene: PackedScene = load(FIGHTER_SCENE)
	var fighter: CharacterBody3D = auto_free(fighter_scene.instantiate())
	add_child(fighter)

	await get_tree().process_frame

	assert_bool(fighter.is_in_group("fighters")).is_true()


## Smoke test: Verify take_damage reduces hp
func test_fighter_take_damage() -> void:
	var fighter_scene: PackedScene = load(FIGHTER_SCENE)
	var fighter: CharacterBody3D = auto_free(fighter_scene.instantiate())
	add_child(fighter)

	await get_tree().process_frame

	var initial_hp: int = fighter.hp
	fighter.take_damage(25)

	assert_int(fighter.hp).is_equal(initial_hp - 25)
