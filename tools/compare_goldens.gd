extends SceneTree
## Golden-image regression check. Compares the freshly rendered PNGs in
## res://screenshots against the committed goldens in res://test/golden using a
## tolerant perceptual metric — llvmpipe (software GL) is not bit-exact run to
## run, so an exact match would flap. Decodes PNGs only (no renderer), so it
## runs plain headless:
##   godot --headless -s tools/compare_goldens.gd
##
## Accept the current renders as the new goldens after an INTENTIONAL visual
## change (there is no local GPU, so goldens must be captured from a CI render —
## fetch the ci-screenshots branch into res://screenshots first, see docs/CI.md):
##   godot --headless -s tools/compare_goldens.gd -- --update
##   # or set GOLDEN_UPDATE=1 in the environment.
##
## Verdict per shot combines two complementary metrics:
##   - changed fraction: share of pixels whose worst channel moved past
##     PIXEL_CHANNEL_TOLERANCE. Catches a broad structural change that churns a
##     large region of the frame.
##   - mean luma delta: average luminance shift across the frame. Catches a
##     uniform darken/brighten (e.g. reverting a lighting fix) that nudges every
##     pixel a little without tripping the per-pixel tolerance.
## A shot fails if EITHER exceeds its threshold. A missing golden warns (so the
## first run of a new shot bootstraps instead of breaking CI); a size mismatch
## fails. Inherently irreproducible shots (see NONGATING) are reported but never
## gate. The gated shots are deterministic, so the thresholds are tight enough
## to catch real regressions in them. See docs/CI.md.

const SHOTS_DIR := "res://screenshots"
const GOLDEN_DIR := "res://test/golden"

# Shots excluded from the pass/fail gate because they are inherently
# irreproducible: they capture the gray-box world's character MID-WALK, and the
# stride phase at capture depends on frame timing, so limbs land in different
# positions each run (02_walking measured 2.4% then 6.3% changed between two
# identical-code runs). They are still rendered, published, and reported here as
# info — just non-gating. The gray-box world's lighting is still guarded by the
# settled 01_world shot; the painted-pipeline shots (the point of this check)
# are deterministic and fully gated.
const NONGATING := ["02_walking.png", "03_dialogue.png"]

# A pixel counts as "changed" when any RGB channel differs by more than this
# (0..255). Below this is llvmpipe dithering / rounding, not a real change.
const PIXEL_CHANNEL_TOLERANCE := 24
# Fail when more than this fraction of pixels changed. The gated shots (painted
# scenes, settled world, journal) all sit at/under 0.6% between identical
# renders, so 2% leaves margin while still catching a broad structural change.
const MAX_CHANGED_FRACTION := 0.02
# Fail when the mean luminance shifts by more than this (0..255). Gated shots
# drift at most ~1.2; reverting a lighting fix shifts the frame by far more.
const MAX_MEAN_LUMA_DELTA := 4.0

var failures: Array[String] = []
var warnings: Array[String] = []


func _initialize() -> void:
	# Failsafe: a script error mid-run would otherwise hang CI until timeout.
	create_timer(120.0).timeout.connect(
		func() -> void:
			printerr("  FAIL: golden compare timed out (script error or hang)")
			quit(1)
	)
	call_deferred("_run")


func _run() -> void:
	var update := _update_mode()
	var golden_abs := ProjectSettings.globalize_path(GOLDEN_DIR)
	DirAccess.make_dir_recursive_absolute(golden_abs)

	var shots := _list_pngs(SHOTS_DIR)
	if shots.is_empty():
		printerr("  FAIL: no screenshots found in %s (did the render step run?)" % SHOTS_DIR)
		quit(1)
		return

	if update:
		for shot_name in shots:
			var src := _load_png("%s/%s" % [SHOTS_DIR, shot_name])
			if src == null:
				printerr("  FAIL: cannot read %s" % shot_name)
				quit(1)
				return
			src.save_png("%s/%s" % [GOLDEN_DIR, shot_name])
			print("  updated golden: %s" % shot_name)
		print("Accepted %d goldens." % shots.size())
		quit(0)
		return

	print("Golden-image regression check (%d shots)" % shots.size())
	for shot_name in shots:
		_compare(shot_name)

	if not warnings.is_empty():
		print("\nWarnings (no golden yet — commit test/golden/<name> to activate):")
		for w in warnings:
			print("  - %s" % w)

	if failures.is_empty():
		print("\nGolden check PASSED")
		quit(0)
	else:
		printerr("\nGolden check FAILED (%d):" % failures.size())
		for f in failures:
			printerr("  - %s" % f)
		printerr(
			(
				"If these changes are intentional, refresh the goldens "
				+ "(see tools/compare_goldens.gd header / docs/CI.md)."
			)
		)
		quit(1)


func _update_mode() -> bool:
	if OS.get_environment("GOLDEN_UPDATE") in ["1", "true", "TRUE"]:
		return true
	return "--update" in OS.get_cmdline_user_args()


# Decode a PNG from raw bytes rather than Image.load(): loading a res:// path
# as an image makes Godot warn that it "should be imported" — noise here, since
# these are freshly rendered / committed reference files we read at runtime.
func _load_png(path: String) -> Image:
	var bytes := FileAccess.get_file_as_bytes(path)
	if bytes.is_empty():
		return null
	var img := Image.new()
	if img.load_png_from_buffer(bytes) != OK:
		return null
	return img


func _list_pngs(dir_path: String) -> PackedStringArray:
	var names := PackedStringArray()
	var dir := DirAccess.open(dir_path)
	if dir == null:
		return names
	for file_name in dir.get_files():
		if file_name.ends_with(".png"):
			names.append(file_name)
	names.sort()
	return names


func _compare(shot_name: String) -> void:
	var golden_path := "%s/%s" % [GOLDEN_DIR, shot_name]
	if not FileAccess.file_exists(golden_path):
		warnings.append(shot_name)
		print("  new:  %s (no golden)" % shot_name)
		return

	var shot := _load_png("%s/%s" % [SHOTS_DIR, shot_name])
	var golden := _load_png(golden_path)
	if shot == null or golden == null:
		failures.append("%s: could not decode image" % shot_name)
		return

	if shot.get_width() != golden.get_width() or shot.get_height() != golden.get_height():
		failures.append(
			(
				"%s: size %dx%d != golden %dx%d"
				% [
					shot_name,
					shot.get_width(),
					shot.get_height(),
					golden.get_width(),
					golden.get_height()
				]
			)
		)
		return

	var metrics := _metrics(shot, golden)
	var changed: float = metrics[0]
	var luma: float = metrics[1]

	if shot_name in NONGATING:
		print(
			(
				"  info  %s  changed=%.2f%%  luma=%.2f  (animated, non-gating)"
				% [shot_name, changed * 100.0, luma]
			)
		)
		return

	var bad := changed > MAX_CHANGED_FRACTION or luma > MAX_MEAN_LUMA_DELTA
	var line := (
		"  %s  %s  changed=%.2f%% (max %.2f%%)  luma=%.2f (max %.2f)"
		% [
			"FAIL" if bad else "ok  ",
			shot_name,
			changed * 100.0,
			MAX_CHANGED_FRACTION * 100.0,
			luma,
			MAX_MEAN_LUMA_DELTA
		]
	)
	if bad:
		printerr(line)
		failures.append("%s: changed=%.2f%% luma=%.2f" % [shot_name, changed * 100.0, luma])
	else:
		print(line)


## Returns [changed_fraction, mean_abs_luma_delta] for two same-size images.
## Works on raw RGBA8 bytes for speed (get_pixel per pixel is far too slow over
## ~750k pixels x 8 shots).
func _metrics(shot: Image, golden: Image) -> Array:
	shot.convert(Image.FORMAT_RGBA8)
	golden.convert(Image.FORMAT_RGBA8)
	var a := shot.get_data()
	var b := golden.get_data()
	var total := a.size() / 4
	if total == 0:
		return [0.0, 0.0]
	var changed := 0
	var luma_sum := 0.0
	var i := 0
	while i < a.size():
		var dr: int = absi(a[i] - b[i])
		var dg: int = absi(a[i + 1] - b[i + 1])
		var db: int = absi(a[i + 2] - b[i + 2])
		if (
			dr > PIXEL_CHANNEL_TOLERANCE
			or dg > PIXEL_CHANNEL_TOLERANCE
			or db > PIXEL_CHANNEL_TOLERANCE
		):
			changed += 1
		# Luminance of the signed per-channel delta (Rec. 601 weights).
		var la := 0.299 * a[i] + 0.587 * a[i + 1] + 0.114 * a[i + 2]
		var lb := 0.299 * b[i] + 0.587 * b[i + 1] + 0.114 * b[i + 2]
		luma_sum += absf(la - lb)
		i += 4
	return [float(changed) / float(total), luma_sum / float(total)]
