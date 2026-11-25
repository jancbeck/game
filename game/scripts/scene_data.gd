## Loads game/config.json and the scene.json it names; resolves data paths and file formats.
##
## Every path inside scene.json is relative to game/. Files are read raw at run time
## (the asset folders carry a .gdignore), so a new export shows up on the next run.
##
## Release data (scripts/release.py build, game/release/): the HDR layers as GPU-compressed .gtx
## files and the depth as lossless PNGs, of every location. A location is read from the release
## data while none of its source files has changed since the build (their mtimes are the
## manifest's); a re-rendered location reads its raw files again and the others keep their release
## data. An exported app always reads the release data: it comes from game_data.pck next to the
## main pack. `--raw` on the command line reads the raw files instead.
extends RefCounted

const Locations := preload("res://scripts/locations.gd")

const RELEASE := "release"
const DATA_PACK := "game_data.pck"
const GTX_MAGIC := "GTX1"
const GTX_HEADER := 20

var config: Dictionary
var scene: Dictionary
var hotspots: Array = []
var data_path: String
var location: String


static var _in_pack := false      # the data comes from game_data.pck, not from assets/
static var _release := -1         # -1 undecided, 0 raw files, 1 release data
static var _stale := {}           # location folder ("" = the start location's assets/) -> true: changed since the build, read raw
static var release_info := {}     # release/manifest.json when the release data is in use


## `loc` names the location to load ("" = the start location of config.json).
func _init(loc := "") -> void:
	_mount_data_pack()
	_decide_release()
	config = _json("config.json")
	location = loc if loc != "" else Locations.start(config)
	data_path = Locations.data_path(config, location)
	if location == Locations.start(config):
		for arg in OS.get_cmdline_user_args():
			if arg.begins_with("--data="):
				data_path = arg.substr(7)
	scene = _json(data_path)
	var hs := data_path.get_base_dir().path_join("hotspots.json")
	hotspots = _json(hs) if FileAccess.file_exists(res(hs)) else []
	print("data: %s: %s (%s)" % [location, data_path, "STAND-IN" if data_path.begins_with("assets_stub") else "export"])


static func res(path: String) -> String:
	return "res://" + path


## A path Godot's file loaders read in the editor and in an exported app alike.
static func abs_path(path: String) -> String:
	return "res://" + path


## An exported app has no assets/ folder: its data is a second pack beside the main one (in
## Contents/Resources of a macOS bundle, next to the executable elsewhere).
static func _mount_data_pack() -> void:
	if _in_pack or DirAccess.dir_exists_absolute("res://assets"):
		return
	var exe_dir := OS.get_executable_path().get_base_dir()
	for dir in [exe_dir.path_join("../Resources"), exe_dir, ProjectSettings.globalize_path("res://")]:
		var pck: String = dir.path_join(DATA_PACK)
		if FileAccess.file_exists(pck) and ProjectSettings.load_resource_pack(pck):
			_in_pack = true
			print("data pack: ", pck)
			return
	push_error("no assets/ folder and no %s next to the game" % DATA_PACK)


## True when release data is in use at all (see uses_release for one source file).
static func release_active() -> bool:
	return _release == 1


## True when the HDR layer or depth file `src` is read from the release data: there is a manifest
## and nothing of the file's location has changed since the build.
static func uses_release(src: String) -> bool:
	return _release == 1 and not _stale.has(_folder_of(src))


## "locations/<name>" for a file of another location, "" for one of the start location.
static func _folder_of(src: String) -> String:
	return "locations/" + src.get_slice("/", 1) if src.begins_with("locations/") else ""


static func _decide_release() -> void:
	if _release >= 0:
		return
	_release = 0
	var manifest := res(RELEASE + "/manifest.json")
	if "--raw" in OS.get_cmdline_user_args():
		print("hdr: raw EXR and depth files (--raw)")
		return
	if not FileAccess.file_exists(manifest):
		print("hdr: raw EXR and depth files (no release data; scripts/release.py build)")
		return
	var info = JSON.parse_string(FileAccess.get_file_as_string(manifest))
	if not info is Dictionary:
		push_warning("release/manifest.json is unreadable; reading raw files")
		return
	var sources: Dictionary = info.get("sources", {})
	var folders := {}
	if not _in_pack:
		for src in sources:
			var rec: Array = sources[src]
			var folder := _folder_of(src)
			folders[folder] = true
			if FileAccess.get_modified_time(res(src)) != int(rec[0]) and not _stale.has(folder):
				_stale[folder] = true
				push_warning("%s changed since the release data was built; reading the raw files of %s (scripts/release.py build)" % [src, folder if folder != "" else "the start location"])
	if not _in_pack and _stale.size() == folders.size():
		print("hdr: raw EXR and depth files (release data is stale)")
		return
	release_info = info
	_release = 1
	print("hdr: release data, %s, built %s, %d locations%s" % [info.get("format", "?"), info.get("built", "?"),
		info.get("locations", []).size(), "" if _stale.is_empty() else ", read raw: %s" % ", ".join(_stale.keys().map(func(k): return k if k != "" else "start location"))])


static func _json(path: String) -> Variant:
	var text := FileAccess.get_file_as_string(res(path))
	if text == "":
		push_error("cannot read " + path)
		return {}
	return JSON.parse_string(text)


static func v3(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])


func has(key: String) -> bool:
	return scene.has(key) and scene[key] != null


## Image from a data path: PNG, EXR (editor builds) or anything else Image can read.
static func image(path: String) -> Image:
	if path == null or path == "":
		return null
	var img := Image.load_from_file(abs_path(path))
	if img == null:
		push_error("cannot load image " + path)
	return img


## float32 little-endian raw image (depth.f32 and friends). The release data stores the same
## bytes as a lossless RGBA8 PNG (release/<path>.png).
static func f32_image(path: String, w: int, h: int) -> Image:
	if uses_release(path):
		var packed := res(RELEASE.path_join(path) + ".png")
		if FileAccess.file_exists(packed):
			var png := Image.load_from_file(packed)
			if png and png.get_width() == w and png.get_height() == h and png.get_format() == Image.FORMAT_RGBA8:
				return Image.create_from_data(w, h, false, Image.FORMAT_RF, png.get_data())
			push_warning("%s does not match %d x %d; reading %s" % [packed, w, h, path])
	var bytes := FileAccess.get_file_as_bytes(res(path))
	if bytes.size() != w * h * 4:
		push_error("%s: %d bytes, expected %d x %d floats" % [path, bytes.size(), w, h])
		return null
	return Image.create_from_data(w, h, false, Image.FORMAT_RF, bytes)


## Where the release data keeps the HDR layer `path` (an EXR of the export).
static func gtx_path(path: String) -> String:
	return RELEASE.path_join(path.get_basename() + ".gtx")


## An EXR of the export as half-float RGBA with mipmaps.
static func hdr_raw(path: String) -> Image:
	var img := image(path)
	if img:
		if img.get_format() != Image.FORMAT_RGBAH:
			img.convert(Image.FORMAT_RGBAH)
		img.generate_mipmaps()
	return img


## An HDR layer: the release data's compressed image (BC6H or ASTC HDR, with mipmaps) when it is
## in use, else the raw EXR. Safe on worker threads once a SceneData exists.
static func hdr_image(path: String) -> Image:
	if uses_release(path):
		var img := read_gtx(gtx_path(path))
		if img:
			return img
		push_warning("no release data for %s; reading the EXR" % path)
	return hdr_raw(path)


## The header of a .gtx file: {format, width, height, mipmaps, flags, raw_size}; {} if unreadable.
static func gtx_header(gtx: String) -> Dictionary:
	var f := FileAccess.open(res(gtx), FileAccess.READ)
	return _gtx_header(f) if f else {}


static func _gtx_header(f: FileAccess) -> Dictionary:
	if f.get_length() < GTX_HEADER or f.get_buffer(4).get_string_from_ascii() != GTX_MAGIC:
		return {}
	var h := {format = f.get_32(), width = f.get_16(), height = f.get_16(), mipmaps = f.get_8() != 0, flags = f.get_8()}
	f.get_16()
	h.raw_size = f.get_32()
	return h


## Reads a .gtx file: a 20-byte header (see release_build.gd), then Image.get_data() of the
## compressed image, zstd-packed when flags & 1.
static func read_gtx(gtx: String) -> Image:
	var f := FileAccess.open(res(gtx), FileAccess.READ)
	if f == null:
		return null
	var h := _gtx_header(f)
	if h.is_empty():
		push_error("%s is not a .gtx file" % gtx)
		return null
	var bytes := f.get_buffer(f.get_length() - GTX_HEADER)
	if int(h.flags) & 1:
		bytes = bytes.decompress(int(h.raw_size), FileAccess.COMPRESSION_ZSTD)
	return Image.create_from_data(h.width, h.height, h.mipmaps, h.format, bytes)


## Frame size in pixels (the camera resolution of the export).
func frame_size() -> Vector2i:
	var r: Array = scene.camera.get("resolution", [2560, 1440])
	return Vector2i(int(r[0]), int(r[1]))
