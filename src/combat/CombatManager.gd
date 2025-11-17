extends Node

## Combat system manager with signals and helper methods for attack detection
## Provides extensible foundation for combos, blocking, and special moves

signal attack_landed(attacker: Node3D, defender: Node3D, damage: int)
signal damage_dealt(fighter: Node3D, amount: int)
signal fighter_defeated(fighter: Node3D)


## Check if two fighters are in range for melee combat
func is_in_attack_range(attacker: Node3D, target: Node3D, max_range: float = 2.0) -> bool:
	if not attacker or not target:
		return false
	return attacker.global_position.distance_to(target.global_position) <= max_range


## Apply damage to a fighter and emit appropriate signals
func apply_damage(attacker: Node3D, defender: Node3D, damage: int) -> void:
	if not defender or not defender.has_method("take_damage"):
		return

	defender.take_damage(damage)
	attack_landed.emit(attacker, defender, damage)
	damage_dealt.emit(defender, damage)

	if defender.has_method("is_defeated") and defender.is_defeated():
		fighter_defeated.emit(defender)


## Register a hitbox collision for damage processing
func process_hitbox_collision(hitbox: Area3D, body: Node3D) -> void:
	var attacker: Node3D = hitbox.get_parent()
	if not attacker or not body:
		return

	# Prevent self-damage
	if attacker == body:
		return

	# Only process if body is a fighter
	if not body.is_in_group("fighters"):
		return

	var damage: int = hitbox.get_meta("damage", 10) if hitbox.has_meta("damage") else 10
	apply_damage(attacker, body, damage)
