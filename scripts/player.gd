extends CharacterBody2D

const SPEED := 160.0

var interact_target : Node = null
var character_sheet : CanvasLayer
var notebook_ui : CanvasLayer

func _ready() -> void:
    $InteractionArea.area_entered.connect(_on_interaction_area_entered)
    $InteractionArea.area_exited.connect(_on_interaction_area_exited)

func _physics_process(delta : float) -> void:
    var input_vector := Vector2.ZERO
    input_vector.x = Input.get_action_strength("move_right") - Input.get_action_strength("move_left")
    input_vector.y = Input.get_action_strength("move_down") - Input.get_action_strength("move_up")
    input_vector = input_vector.normalized()
    velocity = input_vector * SPEED
    move_and_slide()

func _unhandled_input(event : InputEvent) -> void:
    if event.is_action_pressed("interact"):
        _attempt_interact()
    elif event.is_action_pressed("open_character_sheet") and character_sheet:
        character_sheet.call("toggle")
    elif event.is_action_pressed("open_notebook") and notebook_ui:
        notebook_ui.call("toggle")

func _attempt_interact() -> void:
    if interact_target and interact_target.has_method("begin_conversation"):
        interact_target.begin_conversation(self)

func _on_interaction_area_entered(area : Area2D) -> void:
    if area and area.owner and area.owner.is_in_group("npc"):
        interact_target = area.owner

func _on_interaction_area_exited(area : Area2D) -> void:
    if interact_target == area.owner:
        interact_target = null

func set_character_sheet(sheet : CanvasLayer) -> void:
    character_sheet = sheet

func set_notebook_ui(sheet : CanvasLayer) -> void:
    notebook_ui = sheet

func perform_skill_check(skill : String, difficulty : int) -> bool:
    return WorldState.stats.get(skill, 0) + randi_range(1, 20) >= difficulty
