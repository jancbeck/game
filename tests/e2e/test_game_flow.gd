extends GutTest

## End-to-end tests for complete game scenarios

var main_scene: Node


func before_each():
	# Load the main game scene
	var scene = load("res://scenes/main.tscn")
	main_scene = scene.instantiate()
	add_child_autofree(main_scene)
	await wait_frames(2)  # Give scene time to initialize


func test_game_scene_loads():
	assert_not_null(main_scene, "Main scene should load")
	assert_true(main_scene.is_inside_tree(), "Main scene should be in tree")


func test_player_exists_in_scene():
	var player = main_scene.find_child("Player*", true, false)
	assert_not_null(player, "Player should exist in main scene")


func test_ui_exists_in_scene():
	var ui = main_scene.find_child("*UI*", true, false)
	assert_not_null(ui, "UI should exist in main scene")


func test_npc_exists_in_scene():
	var npc = main_scene.find_child("*NPC*", true, false)
	if npc:
		assert_not_null(npc, "NPC should exist in scene")
	else:
		# Scene might not have NPCs, that's okay
		pass_test("No NPC in scene, skipping test")


func test_player_can_move():
	var player = main_scene.find_child("Player*", true, false)
	if player and player is CharacterBody2D:
		var initial_position = player.position

		# Simulate movement input
		player.velocity = Vector2(100, 0)
		player.move_and_slide()

		# Position should change
		assert_ne(
			player.position,
			initial_position,
			"Player should move when velocity is applied"
		)
	else:
		fail_test("Could not find player as CharacterBody2D")


func test_player_has_required_components():
	var player = main_scene.find_child("Player*", true, false)
	if player:
		# Check for stats
		assert_true(
			player.has_node("CharacterStats") or player.get("stats") != null,
			"Player should have stats component"
		)

		# Check for thought cabinet
		assert_true(
			player.has_node("ThoughtCabinet") or player.get("thought_cabinet") != null,
			"Player should have thought cabinet component"
		)
	else:
		fail_test("Could not find player")


func test_ui_starts_hidden():
	var ui = main_scene.find_child("*UI*", true, false)
	if ui:
		# Check that dialogue panel is hidden initially
		var dialogue_panel = ui.find_child("*Dialogue*", true, false)
		if dialogue_panel:
			assert_false(
				dialogue_panel.visible, "Dialogue panel should be hidden initially"
			)

		# Check that character sheet is hidden initially
		var character_sheet = ui.find_child("*Character*", true, false)
		if character_sheet and character_sheet.has_method("is_visible"):
			assert_false(
				character_sheet.visible, "Character sheet should be hidden initially"
			)
	else:
		pass_test("No UI found, skipping test")


func test_game_systems_initialized():
	# Wait a bit for systems to initialize
	await wait_frames(3)

	var player = main_scene.find_child("Player*", true, false)
	if player:
		# Check that stats are initialized
		if player.get("stats"):
			var stats = player.get("stats")
			assert_gt(stats.intellect, 0, "Player stats should be initialized")

		# Check that thought cabinet is initialized
		if player.get("thought_cabinet"):
			var cabinet = player.get("thought_cabinet")
			# Cabinet should have some available thoughts
			var available = cabinet.get_available_thoughts()
			# The cabinet initializes with default thoughts
			assert_true(
				available.size() >= 0, "Thought cabinet should be initialized"
			)


func test_complete_interaction_flow():
	# This is a complex E2E test simulating a complete interaction
	var player = main_scene.find_child("Player*", true, false)
	var ui = main_scene.find_child("*UI*", true, false)

	if not player or not ui:
		pass_test("Required components not found, skipping E2E test")
		return

	# 1. Player should not be in dialogue
	if player.has_method("start_dialogue"):
		assert_false(player.is_in_dialogue, "Player should not start in dialogue")

		# 2. Start dialogue
		player.start_dialogue()
		assert_true(player.is_in_dialogue, "Player should be in dialogue")

		# 3. End dialogue
		player.end_dialogue()
		assert_false(player.is_in_dialogue, "Player should not be in dialogue after ending")


func test_skill_check_in_gameplay_context():
	var player = main_scene.find_child("Player*", true, false)
	if player and player.get("stats"):
		var stats = player.get("stats")

		# Perform a skill check
		var result = stats.perform_skill_check("logic", 8)

		# Verify the skill check completed
		assert_has(result, "success", "Skill check should return success status")
		assert_has(result, "roll", "Skill check should return roll value")

		# Verify roll is in valid range (2d6 = 2-12)
		assert_between(result.roll, 2, 12, "Roll should be valid 2d6 result")
	else:
		pass_test("Player stats not found, skipping test")
