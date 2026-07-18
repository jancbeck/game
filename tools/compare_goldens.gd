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
##     PIXEL_CHANNEL_TOLERANCE. Catches structural changes (a moved character,
##     broken occlusion) that shift a localised region hard.
##   - mean luma delta: average luminance shift across the frame. Catches a
##     uniform darken/brighten (e.g. reverting a lighting fix) that nudges every
##     pixel a little without tripping the per-pixel tolerance.
## A shot fails if EITHER exceeds its threshold. A missing golden warns (so the
## first run of a new shot bootstraps instead of breaking CI); a size mismatch
## fails.

const SHOTS_DIR := "res://screenshots"
const GOLDEN_DIR := "res://test/golden"

# A pixel counts as "changed" when any RGB channel differs by more than this
# (0..255). Below this is llvmpipe dithering / rounding, not a real change.
const PIXEL_CHANNEL_TOLERANCE := 24
# Fail when more than this fraction of pixels changed.
const MAX_CHANGED_FRACTION := 0.02
# Fail when the mean luminance shifts by more than this (0..255).
const MAX_MEAN_LUMA_DELTA := 6.0

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
			var src := Image.new()
			if src.load("%s/%s" % [SHOTS_DIR, shot_name]) != OK:
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

	var shot := Image.new()
	var golden := Image.new()
	if shot.load("%s/%s" % [SHOTS_DIR, shot_name]) != OK or golden.load(golden_path) != OK:
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
