extends Node

# Seamless crossfading music manager for room and aggro tracks

const CROSSFADE_DURATION := 2.0

var room_music: AudioStreamPlayer
var aggro_music: AudioStreamPlayer
var is_aggro_active := false
var is_crossfading := false


func _ready() -> void:
	# Create audio players
	room_music = AudioStreamPlayer.new()
	room_music.stream = load("res://art/music_room_entered_loop.wav")
	room_music.finished.connect(_on_room_music_finished)
	add_child(room_music)

	aggro_music = AudioStreamPlayer.new()
	aggro_music.stream = load("res://art/music_enemies_aggro_loop.wav")
	aggro_music.finished.connect(_on_aggro_music_finished)
	add_child(aggro_music)


func _on_room_music_finished() -> void:
	# When room music loops, restart both tracks to keep them in sync
	room_music.play()
	aggro_music.play()


func _on_aggro_music_finished() -> void:
	# When aggro music loops, restart both tracks to keep them in sync
	room_music.play()
	aggro_music.play()


func start_room_music() -> void:
	# Don't restart if already playing
	if room_music.playing:
		return

	# Start both tracks simultaneously at beginning
	is_aggro_active = false
	room_music.volume_db = 0.0
	aggro_music.volume_db = -40.0  # Quieter but not silent for crossfade

	# Start both tracks so they stay in sync
	room_music.play()
	aggro_music.play()


func trigger_aggro() -> void:
	if is_aggro_active or is_crossfading:
		return

	# Ensure both tracks are playing before crossfading
	if not room_music.playing:
		start_room_music()
		# Wait a frame for playback to start
		await get_tree().process_frame

	is_aggro_active = true
	is_crossfading = true

	# Sync aggro music to current room music position
	var current_pos := room_music.get_playback_position()

	# Make sure aggro track is playing before seeking
	if not aggro_music.playing:
		aggro_music.volume_db = -40.0
		aggro_music.play()
		await get_tree().process_frame

	aggro_music.seek(current_pos)

	# Crossfade between tracks (both audible during transition)
	var tween := create_tween()
	tween.set_parallel(true)
	tween.tween_property(room_music, "volume_db", -40.0, CROSSFADE_DURATION).from(0.0)
	tween.tween_property(aggro_music, "volume_db", 0.0, CROSSFADE_DURATION).from(-40.0)
	tween.finished.connect(func() -> void: is_crossfading = false)


func trigger_calm() -> void:
	if not is_aggro_active or is_crossfading:
		return

	is_aggro_active = false
	is_crossfading = true

	# Sync room music to current aggro music position
	var current_pos := aggro_music.get_playback_position()
	room_music.seek(current_pos)

	# Crossfade between tracks (both audible during transition)
	var tween := create_tween()
	tween.set_parallel(true)
	tween.tween_property(aggro_music, "volume_db", -40.0, CROSSFADE_DURATION).from(0.0)
	tween.tween_property(room_music, "volume_db", 0.0, CROSSFADE_DURATION).from(-40.0)
	tween.finished.connect(func() -> void: is_crossfading = false)


func stop_all() -> void:
	room_music.stop()
	aggro_music.stop()
	is_aggro_active = false
	is_crossfading = false
