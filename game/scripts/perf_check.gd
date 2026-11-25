## Check run for frame times: idles, then loads zoom tiles one after another and zooms onto each,
## so logs/perf.csv shows the steady frame time and any hitch from a tile load.
##   Godot --path game --audio-driver Dummy -- --no-intro --perf-check
extends Node

const TILES := ["forge", "well", "cart", "gallows"]


func _ready() -> void:
	var m := get_parent()
	await get_tree().create_timer(6.0).timeout
	for id in TILES:
		m.compositor.request_tile(id)
		await get_tree().create_timer(1.5).timeout
		m.rig.focus(m.compositor.tile_rect(id).get_center(), 2.0)
		await get_tree().create_timer(2.5).timeout
		m.rig.release()
		await get_tree().create_timer(1.5).timeout
	await get_tree().create_timer(5.5).timeout
	get_tree().quit()
