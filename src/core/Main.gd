extends Node3D

## Main game scene - sets up fighter opponent references


func _ready() -> void:
	var player: Node3D = $Player
	var ai_fighter: Node3D = $AIFighter

	if player and ai_fighter:
		player.opponent = ai_fighter
		ai_fighter.opponent = player
