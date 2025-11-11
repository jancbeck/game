extends Area2D

@export var fire_rate_multiplier: float = 0.65


func _ready() -> void:
	monitoring = true
	$"Sprite".texture = load("res://art/boon.png")
	$"Sprite".centered = true

	# Scale 169x241 boon sprite to 48px height
	var desired_height := 48.0
	var texture_height: int = $"Sprite".texture.get_height()
	var scale_factor: float = desired_height / texture_height
	$"Sprite".scale = Vector2(scale_factor, scale_factor)

	body_entered.connect(_on_body_entered)


func _on_body_entered(body: Node) -> void:
	if body.is_in_group("player"):
		# Play pickup sound
		$"PickupSFX".play()

		# Apply upgrade to persistent state
		PlayerState.apply_boon()

		# Update current player instance immediately
		if "fire_cooldown" in body:
			body.fire_cooldown = PlayerState.fire_cooldown
			var timer := body.get_node("FireCD") as Timer
			if timer:
				timer.wait_time = body.fire_cooldown

		# Hide sprite and disable collision, wait for sound to finish
		$"Sprite".visible = false
		$"CollisionShape2D".set_deferred("disabled", true)
		await $"PickupSFX".finished
		queue_free()
