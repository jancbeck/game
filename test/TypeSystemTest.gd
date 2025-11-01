class_name TypeSystemTest
extends GdUnitTestSuite

## Tests for the type-safe resource system
## Validates NPCDefinition, LocationDefinition, GameAction, and related types


func test_npc_definition_creation():
	"""Test that NPCDefinition can be created with properties"""
	var npc: NPCDefinition = auto_free(NPCDefinition.new())

	npc.npc_id = "test_npc"
	npc.display_name = "Test NPC"
	npc.dialogue_tree_id = "test_dialogue"
	npc.description = "A test NPC for unit testing"

	assert_str(npc.npc_id).is_equal("test_npc")
	assert_str(npc.display_name).is_equal("Test NPC")
	assert_str(npc.dialogue_tree_id).is_equal("test_dialogue")
	assert_str(npc.description).is_equal("A test NPC for unit testing")


func test_npc_definition_to_string():
	"""Test that NPCDefinition provides readable string representation"""
	var npc: NPCDefinition = auto_free(NPCDefinition.new())
	npc.npc_id = "kim"
	npc.display_name = "Kim Kitsuragi"
	npc.dialogue_tree_id = "kim_main"

	var str_repr: String = npc._to_string()
	assert_str(str_repr).contains("kim")
	assert_str(str_repr).contains("Kim Kitsuragi")
	assert_str(str_repr).contains("kim_main")


func test_npc_placement_basic_properties():
	"""Test NPCPlacement resource properties"""
	var placement: NPCPlacement = auto_free(NPCPlacement.new())

	placement.npc_id = "test_npc"
	placement.position = Vector2(100, 200)
	placement.spawn_condition = ""
	placement.dialogue_override = "alt_dialogue"

	assert_str(placement.npc_id).is_equal("test_npc")
	assert_object(placement.position).is_equal(Vector2(100, 200))
	assert_str(placement.dialogue_override).is_equal("alt_dialogue")


func test_npc_placement_should_spawn_always_when_no_condition():
	"""Test that NPCPlacement spawns when no condition is set"""
	var placement: NPCPlacement = auto_free(NPCPlacement.new())
	placement.npc_id = "test_npc"
	placement.spawn_condition = ""

	assert_bool(placement.should_spawn()).is_true()


func test_npc_placement_should_spawn_with_invalid_condition():
	"""Test that NPCPlacement handles invalid spawn conditions gracefully"""
	var placement: NPCPlacement = auto_free(NPCPlacement.new())
	placement.npc_id = "test_npc"
	placement.spawn_condition = "invalid syntax !@#"

	# Should return false for invalid conditions
	assert_bool(placement.should_spawn()).is_false()


func test_location_definition_creation():
	"""Test that LocationDefinition can be created"""
	var location: LocationDefinition = auto_free(LocationDefinition.new())

	location.location_id = "test_location"
	location.display_name = "Test Location"
	location.description = "A test location"
	location.music_state = "exploration"

	assert_str(location.location_id).is_equal("test_location")
	assert_str(location.display_name).is_equal("Test Location")
	assert_str(location.music_state).is_equal("exploration")


func test_location_definition_npc_placements():
	"""Test that LocationDefinition can hold NPC placements"""
	var location: LocationDefinition = auto_free(LocationDefinition.new())
	location.location_id = "town"

	var placement1: NPCPlacement = auto_free(NPCPlacement.new())
	placement1.npc_id = "npc1"
	placement1.position = Vector2(100, 100)

	var placement2: NPCPlacement = auto_free(NPCPlacement.new())
	placement2.npc_id = "npc2"
	placement2.position = Vector2(200, 200)

	location.npc_placements = [placement1, placement2]

	assert_int(location.npc_placements.size()).is_equal(2)
	assert_str(location.npc_placements[0].npc_id).is_equal("npc1")
	assert_str(location.npc_placements[1].npc_id).is_equal("npc2")


func test_location_get_npc_ids():
	"""Test that LocationDefinition can extract NPC IDs"""
	var location: LocationDefinition = auto_free(LocationDefinition.new())

	var placement1: NPCPlacement = auto_free(NPCPlacement.new())
	placement1.npc_id = "merchant"

	var placement2: NPCPlacement = auto_free(NPCPlacement.new())
	placement2.npc_id = "guard"

	location.npc_placements = [placement1, placement2]

	var npc_ids: Array[String] = location.get_npc_ids()
	assert_array(npc_ids).contains(["merchant", "guard"])


func test_location_is_accessible_no_flags():
	"""Test that location is accessible when no flags required"""
	var location: LocationDefinition = auto_free(LocationDefinition.new())
	location.required_flags = []

	assert_bool(location.is_accessible({})).is_true()


func test_location_is_accessible_with_flags():
	"""Test location accessibility based on flags"""
	var location: LocationDefinition = auto_free(LocationDefinition.new())
	location.required_flags = ["flag1", "flag2"]

	# Should not be accessible without flags
	assert_bool(location.is_accessible({})).is_false()

	# Should not be accessible with only one flag
	assert_bool(location.is_accessible({"flag1": true})).is_false()

	# Should be accessible with all flags
	assert_bool(location.is_accessible({"flag1": true, "flag2": true})).is_true()


func test_trigger_zone_creation():
	"""Test TriggerZone creation and properties"""
	var trigger: TriggerZone = auto_free(TriggerZone.new())

	trigger.trigger_id = "test_trigger"
	trigger.area = Rect2(0, 0, 100, 100)
	trigger.trigger_once = true

	assert_str(trigger.trigger_id).is_equal("test_trigger")
	assert_object(trigger.area).is_equal(Rect2(0, 0, 100, 100))
	assert_bool(trigger.trigger_once).is_true()


func test_trigger_zone_can_activate():
	"""Test TriggerZone activation logic"""
	var trigger: TriggerZone = auto_free(TriggerZone.new())
	trigger.trigger_id = "test"

	# Should activate with no conditions
	assert_bool(trigger.can_activate()).is_true()


func test_game_action_set_flag_factory():
	"""Test GameAction.set_flag factory method"""
	var action: GameAction = auto_free(GameAction.set_flag("test_flag", true))

	assert_int(action.action_type).is_equal(GameAction.ActionType.SET_FLAG)
	assert_that(action.parameters).contains_keys(["flag", "value"])
	assert_str(action.parameters["flag"]).is_equal("test_flag")
	assert_bool(action.parameters["value"]).is_true()


func test_game_action_give_item_factory():
	"""Test GameAction.give_item factory method"""
	var action: GameAction = auto_free(GameAction.give_item("sword"))

	assert_int(action.action_type).is_equal(GameAction.ActionType.GIVE_ITEM)
	assert_str(action.parameters["item_id"]).is_equal("sword")


func test_game_action_start_dialogue_factory():
	"""Test GameAction.start_dialogue factory method"""
	var action: GameAction = auto_free(GameAction.start_dialogue("intro_dialogue"))

	assert_int(action.action_type).is_equal(GameAction.ActionType.START_DIALOGUE)
	assert_str(action.parameters["dialogue_id"]).is_equal("intro_dialogue")


func test_game_action_change_music_factory():
	"""Test GameAction.change_music factory method"""
	var action: GameAction = auto_free(GameAction.change_music("combat", 1.5))

	assert_int(action.action_type).is_equal(GameAction.ActionType.CHANGE_MUSIC)
	assert_str(action.parameters["state"]).is_equal("combat")
	assert_float(action.parameters["fade_time"]).is_equal(1.5)


func test_game_action_to_string():
	"""Test that GameAction provides readable string representation"""
	var action: GameAction = auto_free(GameAction.set_flag("test_flag"))

	var str_repr: String = action._to_string()
	assert_str(str_repr).contains("SET_FLAG")
	assert_str(str_repr).contains("test_flag")


func test_entity_registry_has_npc():
	"""Test EntityRegistry.has_npc method"""
	# Should return false for non-existent NPC
	assert_bool(EntityRegistry.has_npc("non_existent")).is_false()


func test_entity_registry_has_location():
	"""Test EntityRegistry.has_location method"""
	# Should return false for non-existent location
	assert_bool(EntityRegistry.has_location("non_existent")).is_false()


func test_entity_registry_get_all_npc_ids():
	"""Test EntityRegistry.get_all_npc_ids returns array"""
	var npc_ids: Array[String] = EntityRegistry.get_all_npc_ids()
	assert_array(npc_ids).is_not_null()


func test_entity_registry_get_all_location_ids():
	"""Test EntityRegistry.get_all_location_ids returns array"""
	var location_ids: Array[String] = EntityRegistry.get_all_location_ids()
	assert_array(location_ids).is_not_null()
