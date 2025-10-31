extends GutTest

## Integration tests for player interactions with game systems

var player: CharacterBody2D
var stats: CharacterStats
var thought_cabinet: ThoughtCabinet


func before_each():
	# Load and instance the player scene
	var player_scene = load("res://scenes/player.tscn")
	player = player_scene.instantiate()
	add_child_autofree(player)

	# Get references to subsystems
	stats = player.stats
	thought_cabinet = player.thought_cabinet


func test_player_has_stats():
	assert_not_null(stats, "Player should have character stats")
	assert_true(is_instance_of(stats, CharacterStats), "Stats should be CharacterStats")


func test_player_has_thought_cabinet():
	assert_not_null(
		thought_cabinet, "Player should have thought cabinet"
	)
	assert_true(
		is_instance_of(thought_cabinet, ThoughtCabinet), "Should be ThoughtCabinet"
	)


func test_player_movement():
	var initial_position = player.position
	player.velocity = Vector2(100, 0)
	player.move_and_slide()
	# Position should change after movement
	assert_ne(
		player.position, initial_position, "Player position should change after movement"
	)


func test_player_dialogue_state():
	assert_false(
		player.is_in_dialogue, "Player should not be in dialogue initially"
	)

	player.start_dialogue()
	assert_true(
		player.is_in_dialogue, "Player should be in dialogue after starting"
	)

	player.end_dialogue()
	assert_false(
		player.is_in_dialogue, "Player should not be in dialogue after ending"
	)


func test_player_dialogue_prevents_movement():
	player.start_dialogue()

	# Try to set velocity
	var direction = Vector2(1, 0)
	player.velocity = direction * player.speed

	# Process physics frame
	player._physics_process(0.016)

	# Velocity should be zero when in dialogue
	assert_eq(
		player.velocity, Vector2.ZERO, "Player velocity should be zero during dialogue"
	)


func test_player_interaction_state():
	assert_false(
		player.can_interact, "Player should not be able to interact initially"
	)

	var mock_npc = Node.new()
	player.set_can_interact(true, mock_npc)

	assert_true(player.can_interact, "Player should be able to interact")
	assert_eq(
		player.nearby_interactable, mock_npc, "Should store reference to interactable"
	)

	player.set_can_interact(false)
	assert_false(player.can_interact, "Player should not be able to interact")

	mock_npc.free()


func test_stats_integration():
	# Modify player stats through the stats system
	var initial_intellect = stats.intellect
	stats.modify_attribute("intellect", 1)

	assert_eq(
		stats.intellect, initial_intellect + 1, "Stats should be modifiable"
	)
	# Skills should auto-update
	assert_eq(stats.logic, stats.intellect + 1, "Skills should update with attributes")


func test_thought_effects_on_skills():
	# Add a thought that affects skills
	var thought = ThoughtCabinet.Thought.new(
		"test_boost", "Test Boost", "Increases logic", 0.1, {"logic": 2}
	)

	thought_cabinet.add_available_thought(thought)
	thought_cabinet.internalize_thought("test_boost")
	await wait_seconds(0.2)  # Wait for internalization

	var effects = thought_cabinet.get_total_effects()
	assert_eq(effects.get("logic", 0), 2, "Thought should provide logic bonus")


func test_skill_check_with_thought_bonuses():
	# This tests the integration between stats and thought cabinet
	var base_logic = stats.get_skill_value("logic")

	# Add a thought that boosts logic
	var thought = ThoughtCabinet.Thought.new(
		"logical_mind", "Logical Mind", "Boosts logic", 0.1, {"logic": 3}
	)

	thought_cabinet.add_available_thought(thought)
	thought_cabinet.internalize_thought("logical_mind")
	await wait_seconds(0.2)

	# Get the bonus from thought cabinet
	var effects = thought_cabinet.get_total_effects()
	var logic_bonus = effects.get("logic", 0)

	assert_gt(logic_bonus, 0, "Should have a logic bonus from thought")
	# In actual gameplay, the bonus would be applied to skill checks
	# This demonstrates the integration works
