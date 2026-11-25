## Builds the release data from the export in assets/ into game/release/, without changing the export.
##
##   hdr    every EXR layer (the main frame, the wide view and every zoom tile: base and light
##          groups) as a GPU-compressed .gtx. Mipmaps are generated first, then the whole chain is
##          compressed to ASTC 4x4 HDR or BC6H, 8 bit per pixel, and stored zstd-packed.
##   depth  every depth.f32 as a lossless PNG of its float bytes (release/<path>.png), checked
##          by reading it back.
##   pack   release/game_data.pck: the files above plus every other runtime file of assets/, luts/
##          and the assets/ of every other location (locations/<name>/assets/), at their res://
##          paths, for the exported app (scripts/release.py export).
##
## The locations are the start location of config.json (the courtyard) and every folder
## locations/<name>/ that has data/scene.json. Each one's layers, wide view and tiles are converted;
## release/ holds them side by side, at the path of their source.
##
## A .gtx file is a 20-byte little-endian header, then the pixels:
##   "GTX1", u32 Image.Format, u16 width, u16 height, u8 has mipmaps, u8 flags (1 = zstd),
##   u16 0, u32 size of the pixels unpacked; then Image.get_data().
## scene_data.gd reads it. release/manifest.json records the format and the mtime and size of
## every source file, which is how the game knows the release data is current.
##
##   Godot --headless --path game --script res://scripts/release_build.gd -- \
##       [--format=astc|bc6h|astc8] [--jobs=N] [--force] [--no-zstd] [--no-pack]
##       [--only=substr,...] [--stats=substr,...] [--out=<dir>]
##
## astc: ASTC 4x4 HDR, about 5 s per 2560 x 1440 layer on one core, so the layers are compressed
## in parallel (--jobs, default all cores). bc6h: Godot's BC6H encoder uses every core by itself
## and takes about 50 s per layer. astc8: ASTC 8x8 HDR, 2 bit per pixel (a size experiment).
## --only converts the files whose path contains one of the substrings, --stats prints the error of
## the compressed layers whose path does, per decade of luminance. Both, and --out (another folder
## than game/release/), are for experiments: they write neither the manifest nor the pack.
extends SceneTree

const SceneData := preload("res://scripts/scene_data.gd")
const Locations := preload("res://scripts/locations.gd")

const FORMATS := {
	"astc": [Image.COMPRESS_ASTC, Image.ASTC_FORMAT_4x4],
	"astc8": [Image.COMPRESS_ASTC, Image.ASTC_FORMAT_8x8],
	"bc6h": [Image.COMPRESS_BPTC, Image.ASTC_FORMAT_4x4],
}
## Files of assets/ that are not part of the game: stills for comparing and debugging.
const DEV_ONLY := ["reference.png", "reference_post.png", "depth_preview.png", ".gdignore", ".DS_Store"]
const ZSTD_MIN_GAIN := 0.9       # keep the zstd-packed pixels only when they are smaller than this share

var format := "astc"
var jobs := 0
var force := false
var zstd := true
var pack := true
var stats: PackedStringArray = []
var only: PackedStringArray = []
var out_root := ""
var hdr_jobs: Array = []         # {src, dst, rel, ...}
var depth_jobs: Array = []       # {src, dst, rel, w, h}
var sources := {}                # src path -> [mtime, size]
var old_sources := {}            # the manifest of the last build
var failed := 0
var location_names: Array[String] = []   # the start location first, then locations/<name>/ with an export


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--format="):
			format = arg.substr(9)
		elif arg.begins_with("--jobs="):
			jobs = int(arg.substr(7))
		elif arg == "--force":
			force = true
		elif arg == "--no-zstd":
			zstd = false
		elif arg == "--no-pack":
			pack = false
		elif arg.begins_with("--stats="):
			stats = arg.substr(8).split(",", false)
		elif arg.begins_with("--only="):
			only = arg.substr(7).split(",", false)
		elif arg.begins_with("--out="):
			out_root = arg.substr(6)
	if not FORMATS.has(format):
		printerr("unknown --format=%s; use %s" % [format, ", ".join(FORMATS.keys())])
		quit(2)
		return
	var t0 := Time.get_ticks_msec()
	var data := SceneData.new()
	var experiment := not only.is_empty() or not stats.is_empty() or out_root != ""
	if out_root == "":
		out_root = _abs(SceneData.RELEASE)
	location_names = _locations(data)
	for name in location_names:
		_collect(data.scene if name == data.location else SceneData.new(name).scene)
	DirAccess.make_dir_recursive_absolute(out_root)
	var f := FileAccess.open(out_root.path_join(".gdignore"), FileAccess.WRITE)
	if f:
		f.close()
	_load_old_manifest()
	_convert_all()
	if failed == 0 and not experiment:
		_write_manifest()
		if pack:
			_pack()
	print("release build: %d HDR layers, %d depth maps, %d failed, %.1f s" % [
		hdr_jobs.size(), depth_jobs.size(), failed, (Time.get_ticks_msec() - t0) / 1000.0])
	quit(1 if failed else 0)


static func _abs(path: String) -> String:
	return ProjectSettings.globalize_path("res://" + path)


## The manifest holds [mtime, size] as JSON, which reads back as floats: compare them as integers.
static func _same_stamp(a: Array, b: Array) -> bool:
	return a.size() == 2 and b.size() == 2 and int(a[0]) == int(b[0]) and int(a[1]) == int(b[1])


func _stamp(src: String) -> Array:
	var p := SceneData.res(src)
	var f := FileAccess.open(p, FileAccess.READ)
	return [FileAccess.get_modified_time(p), f.get_length() if f else 0]


# ---------- what to convert ----------

## The start location, then every other location that has an export (locations/<name>/data/scene.json).
func _locations(start: SceneData) -> Array[String]:
	var out: Array[String] = [start.location]
	var names := DirAccess.get_directories_at(SceneData.res("locations"))
	names.sort()
	for name in names:
		if name != start.location and Locations.exists(start.config, name):
			out.append(name)
	print("locations: %s" % ", ".join(out))
	return out


func _collect(scene: Dictionary) -> void:
	var layers: Dictionary = scene.layers
	var views: Dictionary = scene.get("views", {})
	_hdr(layers.base)
	for g in layers.get("groups", []):
		_hdr(g.image)
	var d: Dictionary = scene.depth
	_depth(d.file, int(d.width), int(d.height))
	var wide: Dictionary = views.get("wide", {})
	if not wide.is_empty():
		_hdr(wide.base)
		for g in wide.get("groups", []):
			_hdr(g.image)
		var wres: Array = wide.camera.get("resolution", [2560, 1440])
		_depth(wide.depth, int(wres[0]), int(wres[1]))
	for t in views.get("tiles", []):
		_hdr(t.base)
		for g in t.get("groups", []):
			_hdr(g.image)
		var size := Vector2(t.rect[2], t.rect[3]) * float(t.get("scale", 2))
		_depth(t.depth, int(size.x), int(size.y))


func _wanted(src: String) -> bool:
	if only.is_empty():
		return true
	for s in only:
		if src.contains(s):
			return true
	return false


func _dst(rel: String) -> String:
	return out_root.path_join(rel.trim_prefix(SceneData.RELEASE + "/"))


func _hdr(src: String) -> void:
	if _wanted(src):
		var rel := SceneData.gtx_path(src)
		hdr_jobs.append({src = src, rel = rel, dst = _dst(rel)})


func _depth(src: String, w: int, h: int) -> void:
	if _wanted(src):
		var rel := SceneData.RELEASE.path_join(src) + ".png"
		depth_jobs.append({src = src, rel = rel, dst = _dst(rel), w = w, h = h})


func _load_old_manifest() -> void:
	var p := out_root.path_join("manifest.json")
	if force or not FileAccess.file_exists(p):
		return
	var m = JSON.parse_string(FileAccess.get_file_as_string(p))
	if m is Dictionary and m.get("format") == format and m.get("zstd") == zstd:
		old_sources = m.get("sources", {})


# ---------- conversion ----------

func _convert_all() -> void:
	var todo: Array = []
	for j in hdr_jobs + depth_jobs:
		j.stamp = _stamp(j.src)
		sources[j.src] = j.stamp
		var current: bool = _same_stamp(old_sources.get(j.src, []), j.stamp) and FileAccess.file_exists(j.dst)
		j.skip = current and not _wants_stats(j.src)
		if not j.skip:
			todo.append(j)
	print("%d of %d files to convert (%s%s)" % [todo.size(), hdr_jobs.size() + depth_jobs.size(), format,
		", zstd" if zstd else ""])
	if todo.is_empty():
		return
	for j in todo:
		DirAccess.make_dir_recursive_absolute(j.dst.get_base_dir())
	var run := func(i: int):
		var j: Dictionary = todo[i]
		var t := Time.get_ticks_msec()
		if j.has("w"):
			_convert_depth(j)
		else:
			_convert_hdr(j)
		j.ms = Time.get_ticks_msec() - t
	# bc6h spreads one layer over all cores itself; asc and the PNGs run one layer per core
	var workers := 1 if format == "bc6h" else (jobs if jobs > 0 else -1)
	var task := WorkerThreadPool.add_group_task(run, todo.size(), workers, true, "release build")
	while not WorkerThreadPool.is_group_task_completed(task):
		OS.delay_msec(500)
	WorkerThreadPool.wait_for_group_task_completion(task)
	for j in todo:
		if j.get("error", "") != "":
			printerr("FAILED %s: %s" % [j.src, j.error])
			failed += 1
		else:
			print("  %-52s %6d ms  %s" % [j.src, j.ms, j.get("note", "")])
	for j in todo:
		if j.get("error", "") == "" and not j.has("w") and _wants_stats(j.src):
			_print_stats(j)


func _convert_hdr(j: Dictionary) -> void:
	var img := SceneData.hdr_raw(j.src)
	if img == null:
		j.error = "cannot read"
		return
	if _wants_stats(j.src):
		j.raw = img.duplicate()
	var spec: Array = FORMATS[format]
	var err = img.compress_from_channels(spec[0], Image.USED_CHANNELS_RGB, spec[1])
	if err != OK:
		j.error = "compress failed: %s" % error_string(err)
		return
	if _wants_stats(j.src):
		j.packed = img.duplicate()
	var pixels := img.get_data()
	var raw_size := pixels.size()
	var flags := 0
	if zstd:
		var z := pixels.compress(FileAccess.COMPRESSION_ZSTD)
		if z.size() < raw_size * ZSTD_MIN_GAIN:
			pixels = z
			flags = 1
	var tmp: String = j.dst + ".part"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		j.error = "cannot write " + tmp
		return
	f.store_buffer(SceneData.GTX_MAGIC.to_ascii_buffer())
	f.store_32(img.get_format())
	f.store_16(img.get_width())
	f.store_16(img.get_height())
	f.store_8(1 if img.has_mipmaps() else 0)
	f.store_8(flags)
	f.store_16(0)
	f.store_32(raw_size)
	f.store_buffer(pixels)
	f.close()
	DirAccess.rename_absolute(tmp, j.dst)
	j.note = "%.1f MB" % (pixels.size() / 1048576.0)


## The float bytes of depth.f32 as the pixels of an RGBA8 PNG: lossless, and PNG's per-channel
## filters take out most of the redundancy. Read back and compared byte for byte.
func _convert_depth(j: Dictionary) -> void:
	var bytes := FileAccess.get_file_as_bytes(SceneData.res(j.src))
	if bytes.size() != j.w * j.h * 4:
		j.error = "%d bytes, expected %d x %d floats" % [bytes.size(), j.w, j.h]
		return
	var png := Image.create_from_data(j.w, j.h, false, Image.FORMAT_RGBA8, bytes)
	var err := png.save_png(j.dst)
	if err != OK:
		j.error = "save_png: %s" % error_string(err)
		return
	var back := Image.load_from_file(j.dst)
	if back == null or back.get_format() != Image.FORMAT_RGBA8 or back.get_data() != bytes:
		j.error = "the PNG does not read back identical"
		return
	j.note = "%.1f MB of %.1f MB" % [FileAccess.open(j.dst, FileAccess.READ).get_length() / 1048576.0, bytes.size() / 1048576.0]


# ---------- error of the compression ----------

func _wants_stats(src: String) -> bool:
	for s in stats:
		if src.contains(s):
			return true
	return false


const BANDS := [0.0, 0.001, 0.01, 0.1, 1.0, 1e9]
const BAND_NAMES := ["< 0.001", "0.001 - 0.01", "0.01 - 0.1", "0.1 - 1", ">= 1"]


## Compares the compressed layer with the source on every second pixel in x and y: per decade of
## luminance, the mean and the 99th percentile of the error in stops (log2 of the ratio), and the
## largest absolute error.
func _print_stats(j: Dictionary) -> void:
	var raw: Image = j.raw
	var rec: Image = j.packed
	rec.decompress()
	raw.clear_mipmaps()
	rec.clear_mipmaps()
	raw.convert(Image.FORMAT_RGBAF)
	rec.convert(Image.FORMAT_RGBAF)
	var a := raw.get_data().to_float32_array()
	var b := rec.get_data().to_float32_array()
	var w := raw.get_width()
	var h := raw.get_height()
	var stops: Array = []
	var maxabs: Array = []
	for i in BANDS.size() - 1:
		stops.append([])
		maxabs.append(0.0)
	var eps := 1e-5
	for y in range(0, h, 2):
		for x in range(0, w, 2):
			var o := (y * w + x) * 4
			var lum := 0.2126 * a[o] + 0.7152 * a[o + 1] + 0.0722 * a[o + 2]
			var band := 0
			while band < BANDS.size() - 2 and lum >= BANDS[band + 1]:
				band += 1
			for c in 3:
				var va := a[o + c]
				var vb := b[o + c]
				maxabs[band] = maxf(maxabs[band], absf(va - vb))
			var la := 0.2126 * b[o] + 0.7152 * b[o + 1] + 0.0722 * b[o + 2]
			stops[band].append(absf(log(maxf(la, eps) / maxf(lum, eps)) / log(2.0)))
	var line := "  stats %s (luminance decade: share, mean / p99 error in stops, max abs error)" % j.src
	for band in stops.size():
		var s: Array = stops[band]
		if s.is_empty():
			continue
		s.sort()
		var mean := 0.0
		for v in s:
			mean += v
		line += "\n    %s %5.1f%%  %.3f / %.3f  %.5f" % [String(BAND_NAMES[band]).rpad(14),
			100.0 * s.size() / (w * h / 4), mean / s.size(), s[mini(s.size() - 1, int(s.size() * 0.99))], maxabs[band]]
	print(line)


# ---------- manifest and pack ----------

func _write_manifest() -> void:
	var m := {format = format, zstd = zstd, built = Time.get_datetime_string_from_system(), locations = location_names, sources = sources}
	var f := FileAccess.open(out_root.path_join("manifest.json"), FileAccess.WRITE)
	f.store_string(JSON.stringify(m, "\t"))
	f.close()


## The data of the exported app, at the res:// paths the game reads: the converted files under
## release/, every other file of assets/, luts/ and the assets/ of the other locations. EXRs and
## depth files that were converted stay out; so do the stills for comparing. The scene.json,
## hotspots.json and the rest of data/ go into the main pack (export_presets.cfg include_filter).
func _pack() -> void:
	var out := out_root.path_join(SceneData.DATA_PACK)
	var packer := PCKPacker.new()
	if packer.pck_start(out) != OK:
		printerr("cannot start " + out)
		failed += 1
		return
	var converted := {}
	var n := 0
	packer.add_file("res://release/manifest.json", out_root.path_join("manifest.json"))
	for j in hdr_jobs + depth_jobs:
		converted[j.src] = true
		packer.add_file("res://" + j.rel, j.dst)
		n += 1
	var skipped := 0
	var dirs: Array[String] = ["assets", "luts"]
	for name in location_names:
		if name != location_names[0]:
			dirs.append("locations/%s/assets" % name)
	for dir in dirs:
		for rel in _walk(dir):
			var name: String = rel.get_file()
			if name in DEV_ONLY or (converted.has(rel) and rel.get_extension() in ["exr", "f32"]):
				skipped += 1
				continue
			packer.add_file("res://" + rel, _abs(rel))
			n += 1
	if packer.flush() != OK:
		printerr("cannot write " + out)
		failed += 1
		return
	print("pack: %d files from %s (%d left out), %.0f MB, %s" % [n, ", ".join(dirs), skipped,
		FileAccess.open(out, FileAccess.READ).get_length() / 1048576.0, out])


## Every file below a res:// directory, as paths relative to res:// (directories are followed,
## also when the directory itself is a symlink).
func _walk(dir: String) -> Array:
	var files: Array = []
	var d := DirAccess.open(SceneData.res(dir))
	if d == null:
		return files
	for sub in d.get_directories():
		files.append_array(_walk(dir.path_join(sub)))
	for f in d.get_files():
		files.append(dir.path_join(f))
	return files
