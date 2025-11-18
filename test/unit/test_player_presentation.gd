class_name TestPlayerPresentation
extends GdUnitTestSuite

const GameStateScript = preload("res://scripts/core/game_state.gd")
const PlayerPresentation = preload("res://scripts/presentation/player_presentation.gd")

var _game_state: GameStateScript
var _player_presentation_mock: PlayerPresentation
var _mesh_instance: MeshInstance3D
var _capsule_mesh: CapsuleMesh
var _material: StandardMaterial3D


func before_test():
	_game_state = GameStateScript.new()
	_game_state._initialize_state()

	# Manually create a mock PlayerPresentation instance and its dependencies
	_player_presentation_mock = PlayerPresentation.new()
	_player_presentation_mock.game_state = _game_state # Inject mock

	_mesh_instance = MeshInstance3D.new()
	_mesh_instance.name = "MeshInstance3D"  # Set the name for @onready (matches $MeshInstance3D)
	_player_presentation_mock.add_child(_mesh_instance)  # Add mesh as child BEFORE adding parent to tree

	add_child(_player_presentation_mock)  # Add to scene tree, triggering _ready

	_capsule_mesh = CapsuleMesh.new()  # Create a basic mesh
	_material = StandardMaterial3D.new()  # Create a default material

	_mesh_instance.mesh = _capsule_mesh  # Assign the mesh
	_mesh_instance.set_surface_override_material(0, _material)  # Set the override material

	# Allow _ready() to fully process, which includes `call_deferred` for _on_state_changed
	await get_tree().process_frame


func after_test():
	if _player_presentation_mock:
		_player_presentation_mock.queue_free()  # Free the mock PlayerPresentation and its children
	if _game_state:
		_game_state.free()


func test_player_color_changes_with_flexibility_stats():
	# Arrange
	var player_presentation = _player_presentation_mock

	# Initial state: all flexibility stats at 10 (should be green-ish)
	# Color is (1.0 - avg_flex / 10.0, avg_flex / 10.0, 0.5)
	# Expected: (0.0, 1.0, 0.5)
	var initial_flex_state = _game_state.state.duplicate(true)
	initial_flex_state["player"]["flexibility"] = {"charisma": 10, "cunning": 10, "empathy": 10}
	_game_state.dispatch(func(s): return initial_flex_state)

	# Allow time for deferred calls and _on_state_changed to process
	await get_tree().process_frame

	var initial_material = (
		player_presentation.mesh.get_surface_override_material(0) as StandardMaterial3D
	)
	var initial_color = initial_material.albedo_color

	# Act: Change flexibility stats to simulate degradation (should be red-ish)
	var degraded_flex_state = _game_state.state.duplicate(true)
	degraded_flex_state["player"]["flexibility"] = {"charisma": 1, "cunning": 1, "empathy": 1}
	_game_state.dispatch(func(s): return degraded_flex_state)

	# Allow time for deferred calls and _on_state_changed to process
	await get_tree().process_frame
	var degraded_material = (
		player_presentation.mesh.get_surface_override_material(0) as StandardMaterial3D
	)
	var degraded_color = degraded_material.albedo_color

	# Assert
	# Using `is_equal_approx` for float comparisons
	assert_that(initial_color.r).is_equal_approx(0.0, 0.001)
	assert_that(initial_color.g).is_equal_approx(1.0, 0.001)
	assert_that(initial_color.b).is_equal_approx(0.5, 0.001)

	assert_that(degraded_color.r).is_equal_approx(0.9, 0.001)
	assert_that(degraded_color.g).is_equal_approx(0.1, 0.001)
	assert_that(degraded_color.b).is_equal_approx(0.5, 0.001)

	# Ensure color actually changed
	assert_that(initial_color).is_not_equal(degraded_color)
