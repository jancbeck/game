extends Node

# Persistent player state that survives room transitions
const MIN_FIRE_COOLDOWN: float = 0.05

var fire_cooldown: float = 0.18


func apply_boon() -> void:
	# Each boon reduces cooldown by 35%, clamped to minimum
	fire_cooldown *= 0.65
	fire_cooldown = max(fire_cooldown, MIN_FIRE_COOLDOWN)


func is_max_fire_rate() -> bool:
	return fire_cooldown <= MIN_FIRE_COOLDOWN


func reset() -> void:
	# Called on player death to reset all upgrades
	fire_cooldown = 0.18
