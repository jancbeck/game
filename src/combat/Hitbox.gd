extends Area3D

## Hitbox for attack detection
## Attach to fighter and enable/disable during attack animations

@export var damage: int = 10
@export var knockback_force: float = 5.0

var is_active: bool = false


func _ready() -> void:
	monitoring = false
	body_entered.connect(_on_body_entered)
	set_meta("damage", damage)


func activate() -> void:
	is_active = true
	monitoring = true


func deactivate() -> void:
	is_active = false
	monitoring = false


func _on_body_entered(body: Node3D) -> void:
	if not is_active:
		return

	CombatManager.process_hitbox_collision(self, body)
