extends CharacterBody2D

## Player character controller

@export var speed: float = 200.0
@export var stats: CharacterStats
@export var thought_cabinet: ThoughtCabinet

var is_in_dialogue: bool = false
var can_interact: bool = false
var nearby_interactable = null


func _ready():
	# Initialize character systems if not assigned in editor
	if not stats:
		stats = CharacterStats.new()
		add_child(stats)

	if not thought_cabinet:
		thought_cabinet = ThoughtCabinet.new()
		add_child(thought_cabinet)


func _physics_process(_delta):
	if is_in_dialogue:
		velocity = Vector2.ZERO
	else:
		handle_movement()

	move_and_slide()


func handle_movement():
	var direction = Vector2.ZERO

	if Input.is_action_pressed("move_up"):
		direction.y -= 1
	if Input.is_action_pressed("move_down"):
		direction.y += 1
	if Input.is_action_pressed("move_left"):
		direction.x -= 1
	if Input.is_action_pressed("move_right"):
		direction.x += 1

	if direction.length() > 0:
		direction = direction.normalized()
		velocity = direction * speed
	else:
		velocity = Vector2.ZERO


func _input(event):
	if event.is_action_pressed("interact") and can_interact and nearby_interactable:
		interact_with(nearby_interactable)

	if event.is_action_pressed("open_character_sheet"):
		toggle_character_sheet()

	if event.is_action_pressed("open_thought_cabinet"):
		toggle_thought_cabinet()


func interact_with(interactable):
	if interactable.has_method("interact"):
		interactable.interact(self)


func toggle_character_sheet():
	# Signal UI to show/hide character sheet
	get_tree().call_group("ui", "toggle_character_sheet")


func toggle_thought_cabinet():
	# Signal UI to show/hide thought cabinet
	get_tree().call_group("ui", "toggle_thought_cabinet")


func set_can_interact(value: bool, interactable = null):
	can_interact = value
	nearby_interactable = interactable
	if value:
		get_tree().call_group("ui", "show_interact_prompt")
	else:
		get_tree().call_group("ui", "hide_interact_prompt")


func start_dialogue():
	is_in_dialogue = true


func end_dialogue():
	is_in_dialogue = false
