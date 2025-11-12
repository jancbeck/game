extends CanvasLayer


func _process(_d: float) -> void:
	var n := get_tree().get_nodes_in_group("enemies").size()
	$"Lbl".text = "Enemies: " + str(n)

	# Update player stats display
	var players := get_tree().get_nodes_in_group("player")
	if players.size() > 0:
		var player := players[0]
		if "fire_cooldown" in player:
			var cooldown: float = player.fire_cooldown
			var shots_per_sec: float = 1.0 / cooldown if cooldown > 0 else 0.0
			$"FireRate".text = "Fire Rate: %.1f shots/s" % shots_per_sec

		if "hp" in player and "max_hp" in player:
			$"HealthBar".max_value = player.max_hp
			$"HealthBar".value = player.hp
			$"HealthLabel".text = "HP: %d / %d" % [player.hp, player.max_hp]
