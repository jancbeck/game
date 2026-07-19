extends GdUnitTestSuite
## The playable convict: art/models/convict.glb (built by
## tools/build_convict.py) wrapped by ConvictRig, driven through the same
## animate/set_speaking/face_direction interface the procedural rigs use.
## These tests prove the model instantiates with its skeleton and clips and
## that the driver picks the right clip for each state — no renderer needed.

var rig: ConvictRig


func before_test() -> void:
	rig = auto_free(ConvictRig.new())
	add_child(rig)  # entering the tree runs _ready -> _build


func test_builds_model_with_skeleton_and_looping_clips() -> void:
	assert_object(rig._anim).is_not_null()
	assert_bool(rig.has_clips()).is_true()
	assert_object(rig._model.find_child("Skeleton3D", true, false)).is_not_null()
	for clip in ["idle", "walk", "talk"]:
		var animation := rig._anim.get_animation(clip)
		assert_int(animation.loop_mode).is_equal(Animation.LOOP_LINEAR)


func test_starts_in_idle() -> void:
	assert_str(rig.current_clip()).is_equal("idle")


func test_animate_picks_clip_for_each_state() -> void:
	rig.animate(0.1, 1.0)
	assert_str(rig.current_clip()).is_equal("walk")
	rig.animate(0.1, 0.0)
	assert_str(rig.current_clip()).is_equal("idle")
	rig.set_speaking(true)
	rig.animate(0.1, 0.0)
	assert_str(rig.current_clip()).is_equal("talk")
	rig.set_speaking(false)
	rig.animate(0.1, 0.0)
	assert_str(rig.current_clip()).is_equal("idle")


func test_freeze_clip_holds_an_exact_pose() -> void:
	rig.freeze_clip("walk", 0.2)
	assert_str(rig.current_clip()).is_equal("walk")
	assert_bool(rig._anim.is_playing()).is_false()
	assert_float(rig._anim.current_animation_position).is_equal_approx(0.2, 0.001)


func test_build_scalar_scales_the_model() -> void:
	# Typed explicitly: auto_free() returns Variant, and `:=` inference from a
	# Variant is a warning — gdUnit4 discovery compiles warnings as errors.
	var big: ConvictRig = auto_free(ConvictRig.new())
	big.build = 1.2
	add_child(big)
	assert_float(big._model.scale.x).is_equal_approx(1.2, 0.001)


func test_face_direction_turns_toward_the_target() -> void:
	# Inherited from CharacterRig: weight 1.0 lands exactly on the target.
	rig.face_direction(Vector3(1, 0, 0), 1.0, 1.0)
	assert_float(rig.rotation.y).is_equal_approx(-PI / 2.0, 0.001)


func test_palette_is_a_safe_noop() -> void:
	# Manifest code assigns colors to every character; the convict's colors
	# are baked, so this must do nothing — and must not rebuild or error.
	rig.set_palette(Color.RED, Color.BLUE)
	assert_bool(rig.has_clips()).is_true()
