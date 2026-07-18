class_name ConvictRig
extends CharacterRig
## The playable convict: a Blender-built, rigged, animated 3D model
## (art/models/convict.glb — mesh, skeleton, and the idle/walk/talk clips
## are all authored by tools/build_convict.py, so rig and mesh can never
## mismatch). Drop-in replacement for the procedural CharacterRig wherever
## the PLAYER is concerned: same animate()/set_speaking()/face_direction()
## interface, same blob shadow, same `build` scaling. NPCs stay procedural.

const MODEL := preload("res://art/models/convict.glb")
## Crossfade between clips, seconds.
const BLEND := 0.25

var _model: Node3D
var _anim: AnimationPlayer
var _current := ""


func _build() -> void:
	_model = MODEL.instantiate()
	# glTF assets face +Z; the painted scene's facing math (inherited from
	# CharacterRig) aims -Z down the walk direction — spin the model so its
	# front agrees with the rig's forward.
	_model.rotation.y = PI
	_model.scale = Vector3.ONE * build
	add_child(_model)
	_anim = _model.find_child("AnimationPlayer", false, false) as AnimationPlayer
	if _anim == null:
		push_error("ConvictRig: convict.glb has no AnimationPlayer")
		return
	for clip in ["idle", "walk", "talk"]:
		var animation := _anim.get_animation(clip)
		if animation == null:
			push_error("ConvictRig: convict.glb is missing the '%s' clip" % clip)
			continue
		animation.loop_mode = Animation.LOOP_LINEAR
	_play("idle")
	_add_blob_shadow()


## Soft contact-shadow blob so the convict sits ON the painting (same trick
## as the procedural rigs).
func _add_blob_shadow() -> void:
	var blob := MeshInstance3D.new()
	var blob_mesh := PlaneMesh.new()
	blob_mesh.size = Vector2(0.9, 0.9)
	var blob_mat := StandardMaterial3D.new()
	blob_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	blob_mat.albedo_color = Color(0, 0, 0, 0.45)
	blob_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	blob_mesh.material = blob_mat
	blob.mesh = blob_mesh
	blob.position.y = 0.02
	add_child(blob)


## Palette is baked into the model's materials — the convict's look is data
## from the sprite, not the manifest. Kept as a no-op so manifest code that
## assigns colors cannot break anything.
func set_palette(_body: Color, _head: Color) -> void:
	pass


## drive with speed in [0..1]; 0 = idle (or the talking loop while speaking)
func animate(_delta: float, speed: float) -> void:
	if _anim == null:
		return
	if speed > 0.05:
		# Match stride rate to travel pace; speed_scale is player-wide, so it
		# is only nudged while the walk clip is up.
		_anim.speed_scale = 0.6 + 0.5 * speed
		_play("walk")
	else:
		_anim.speed_scale = 1.0
		_play("talk" if _speaking else "idle")


func _play(clip: String) -> void:
	if _current == clip:
		return
	_current = clip
	_anim.play(clip, BLEND)


## True when the GLB shipped all three clips (the "animated" in rigged &
## animated — asserted by CI).
func has_clips() -> bool:
	if _anim == null:
		return false
	for clip in ["idle", "walk", "talk"]:
		if not _anim.has_animation(clip):
			return false
	return true


## The clip currently driving the model (test/screenshot probe).
func current_clip() -> String:
	return _current


## Freeze a clip at an exact timestamp — deterministic framing for the
## rendered screenshot review, independent of wall-clock playback.
func freeze_clip(clip: String, time: float) -> void:
	if _anim == null:
		return
	_play(clip)
	_anim.pause()
	_anim.seek(time, true)
