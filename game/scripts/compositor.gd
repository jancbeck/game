## Background compositor: base and light-group layers summed in linear light, each group scaled
## by its source's flicker curve, with the frame's depth written for occlusion.
##
## Three sources of the same picture, chosen per pixel by the camera's view (camera_rig.gd):
##   main   the 2560 x 1440 frame (scene.json -> layers, depth, masks)
##   wide   views.wide: twice the frame's width and height at half density, for zoom < 1;
##          freed once the intro has zoomed in
##   tile   views.tiles[i]: a hotspot's 1280 x 720 frame-px area at 2x density. Files are decoded on
##          a worker thread; the GPU textures are one fixed set allocated at start (the tile slot)
##          and refilled one texture or array layer per frame, so a tile never stalls a frame.
##          thread when the camera focuses that hotspot, blended in above zoom 1.2
## Each source may carry ids (8-bit, k = hotspot k), which drive the hover outline.
extends Node3D

const SceneData := preload("res://scripts/scene_data.gd")
const Curves := preload("res://scripts/curves.gd")
const MAX_GROUPS := 16
const TILE_LAYERS := 10           # light groups a tile can hold (the main frame has 10)
const MAX_IDS := 32
const CANVAS := Vector2(2560, 1440)

var groups: Array = []            # [{id, curve, seed, anchor: Vector3}]
var levels := {}                  # id -> curve level at the current time
var intensities := {}             # id -> layer intensity (level^1.3)
var depth_img: Image
var ids_img: Image
var masks := {}                   # key -> Image (main frame)
var mat: ShaderMaterial
var frozen := false               # every group at intensity 1 (tonemap check)
var frame := Vector2(2560, 1440)

var wide := {}                    # {rect: Rect2 frame px, depth: Image, ids: Image, offset, group_ids}
var tile_defs := {}               # hotspot id -> tile entry of scene.json
var tile := {}                    # the loaded tile: {id, def, rect, scale, depth, ids, group_ids, tex}
var tile_mix := 0.0
var _tile_task := -1
var _tile_pending := {}
var _slot := {}                   # the tile textures: base, groups (array), depth, ids, puddle, wet
var slot_format := Image.FORMAT_RGBAH   # of the HDR textures in the slot
var _stage: Array[Callable] = []  # upload steps of the tile being swapped in, one per frame
var _upload_us := 0
var perf                          # perf.gd, to blame hitches on tile uploads
var highlight := PackedFloat32Array()


func setup(data: SceneData) -> void:
	frame = Vector2(data.frame_size())
	mat = ShaderMaterial.new()
	mat.shader = load("res://shaders/background.gdshader")
	highlight.resize(MAX_IDS)
	var layers: Dictionary = data.scene.layers
	var views: Dictionary = data.scene.get("views", {})
	var fs := data.frame_size()

	var t0 := Time.get_ticks_msec()
	var paths: Array = [layers.base]
	for g in layers.get("groups", []):
		paths.append(g.image)
	var wv: Dictionary = views.get("wide", {})
	if not data.config.get("camera", {}).get("intro", true):
		wv = {}
	var n_main := paths.size()
	if not wv.is_empty():
		paths.append(wv.base)
		for g in wv.get("groups", []):
			paths.append(g.image)
	var imgs := load_hdr_parallel(paths)

	mat.set_shader_parameter("base_tex", ImageTexture.create_from_image(_fit(imgs[0], fs, layers.base)))
	var layer_imgs: Array[Image] = []
	var gi := 1
	for g in layers.get("groups", []):
		var img: Image = imgs[gi]
		gi += 1
		if img == null:
			continue
		if layer_imgs.size() == MAX_GROUPS:
			push_error("more than %d light groups; the rest are ignored" % MAX_GROUPS)
			break
		layer_imgs.append(_fit(img, fs, g.image))
		groups.append({id = g.id, curve = g.get("curve", "fire"), seed = int(g.get("seed", Curves.seed_of(g.id))),
			anchor = SceneData.v3(g.anchor) if g.get("anchor") else Vector3.INF})
	mat.set_shader_parameter("groups_tex", _array(layer_imgs))
	mat.set_shader_parameter("group_count", groups.size())

	var dm: Dictionary = data.scene.depth
	depth_img = SceneData.f32_image(dm.file, int(dm.width), int(dm.height))
	if depth_img.get_size() != fs:
		push_error("depth %s differs from the frame %s" % [depth_img.get_size(), fs])
	mat.set_shader_parameter("depth_m", ImageTexture.create_from_image(depth_img))
	var mk: Dictionary = data.scene.get("masks", {})
	for key in ["puddle", "wet"]:
		var img := SceneData.image(mk.get(key, ""))
		if img == null:
			img = Image.create(4, 4, false, Image.FORMAT_L8)
			img.fill(Color(0.5, 0.5, 0.5) if key == "wet" else Color.BLACK)
		img.convert(Image.FORMAT_L8)
		masks[key] = img
		mat.set_shader_parameter(key + "_tex", ImageTexture.create_from_image(img))
	ids_img = _ids_image(mk.get("ids", ""))
	mat.set_shader_parameter("ids_tex", ImageTexture.create_from_image(ids_img if ids_img else _blank_ids()))
	mat.set_shader_parameter("frame_size", frame)

	if not wv.is_empty():
		_setup_wide(data, wv, imgs.slice(n_main))
	for t in views.get("tiles", []):
		tile_defs[String(t.get("hotspot", t.id))] = t
	_alloc_tile_slot()
	mat.set_shader_parameter("tile_mix", 0.0)
	print("layers: base + %d groups%s loaded in %d ms; %d zoom tiles listed" % [groups.size(),
		" + wide view" if not wide.is_empty() else "", Time.get_ticks_msec() - t0, tile_defs.size()])

	var quad := QuadMesh.new()
	quad.size = Vector2(2, 2)
	var mi := MeshInstance3D.new()
	mi.name = "Background"
	mi.mesh = quad
	mi.material_override = mat
	mi.extra_cull_margin = 16384.0
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	update(0.0)


## Loads HDR layers on worker threads, with mipmaps (half-float, or GPU-compressed in release
## data); keeps the order of paths (null on error).
static func load_hdr_parallel(paths: Array) -> Array:
	var out := []
	out.resize(paths.size())
	var job := func(i: int):
		out[i] = SceneData.hdr_image(paths[i])
	var task := WorkerThreadPool.add_group_task(job, paths.size(), -1, true, "load layers")
	WorkerThreadPool.wait_for_group_task_completion(task)
	return out


func _fit(img: Image, fs: Vector2i, path: String) -> Image:
	if img.get_size() != fs:
		push_warning("%s is %s, expected %s" % [path, img.get_size(), fs])
		if img.is_compressed():
			img.decompress()
		img.resize(fs.x, fs.y, Image.INTERPOLATE_BILINEAR)
		img.generate_mipmaps()
	return img


static func _array(imgs: Array[Image]) -> Texture2DArray:
	if imgs.is_empty():
		var blank := Image.create(8, 8, false, Image.FORMAT_RGBAH)
		blank.generate_mipmaps()
		imgs.append(blank)  # the array needs one layer
	var arr := Texture2DArray.new()
	arr.create_from_images(imgs)
	return arr


static func _ids_image(path) -> Image:
	if path == null or path == "":
		return null
	var img := SceneData.image(path)
	if img:
		img.convert(Image.FORMAT_L8)
	return img


static func _blank_ids() -> Image:
	return Image.create(4, 4, false, Image.FORMAT_L8)


## The wide view's rectangle in frame px, from its camera (same direction as the main camera).
func _setup_wide(data: SceneData, wv: Dictionary, imgs: Array) -> void:
	var c: Dictionary = data.scene.camera
	var wc: Dictionary = wv.camera
	var ppm := float(c.px_per_m)
	var d := SceneData.v3(wc.origin) - SceneData.v3(c.origin)
	var size := Vector2(float(wc.ortho_width_m), float(wc.ortho_height_m)) * ppm
	var centre := frame * 0.5 + Vector2(d.dot(SceneData.v3(c.basis_x)), -d.dot(SceneData.v3(c.basis_y))) * ppm
	var rect := Rect2(centre - size * 0.5, size)
	var fwd := -SceneData.v3(c.basis_z).normalized()
	var res: Array = wc.get("resolution", [2560, 1440])
	var ws := Vector2i(int(res[0]), int(res[1]))
	var group_imgs: Array[Image] = []
	var ids_order: Array = []
	var wgroups: Array = wv.get("groups", [])
	for i in wgroups.size():
		if imgs[i + 1] == null:
			continue
		group_imgs.append(_fit(imgs[i + 1], ws, wgroups[i].image))
		ids_order.append(wgroups[i].id)
	wide = {rect = rect, offset = d.dot(fwd), group_ids = ids_order,
		depth = SceneData.f32_image(wv.depth, ws.x, ws.y), ids = _ids_image(wv.get("ids", ""))}
	mat.set_shader_parameter("wide_on", true)
	mat.set_shader_parameter("wide_base", ImageTexture.create_from_image(_fit(imgs[0], ws, wv.base)))
	mat.set_shader_parameter("wide_groups", _array(group_imgs))
	mat.set_shader_parameter("wide_count", group_imgs.size())
	mat.set_shader_parameter("wide_depth", ImageTexture.create_from_image(wide.depth))
	mat.set_shader_parameter("wide_ids", ImageTexture.create_from_image(wide.ids if wide.ids else _blank_ids()))
	mat.set_shader_parameter("wide_rect", _uv_rect(rect))
	mat.set_shader_parameter("wide_offset", wide.offset)
	mat.set_shader_parameter("wide_lod_bias", log(ws.x / rect.size.x) / log(2.0))


## Frees the wide view (after the intro; it is only seen below zoom 1).
func drop_wide() -> void:
	if wide.is_empty():
		return
	wide = {}
	mat.set_shader_parameter("wide_on", false)
	for k in ["wide_base", "wide_groups", "wide_depth", "wide_ids"]:
		mat.set_shader_parameter(k, null)
	print("wide view freed")


func _uv_rect(r: Rect2) -> Vector4:
	return Vector4(r.position.x / frame.x, r.position.y / frame.y, r.size.x / frame.x, r.size.y / frame.y)


# ---------- zoom tiles ----------

func has_tile(hotspot_id: String) -> bool:
	return tile_defs.has(hotspot_id)


func tile_rect(hotspot_id: String) -> Rect2:
	var r: Array = tile_defs[hotspot_id].rect
	return Rect2(r[0], r[1], r[2], r[3])


func tile_ready(hotspot_id: String) -> bool:
	return not tile.is_empty() and tile.id == hotspot_id


## The tile textures, allocated once at the tile size with blank images (the upload of blank
## layers happens during loading, not in play). The HDR textures have the format of the release
## data's tiles (compressed), or half-float for raw EXRs.
func _alloc_tile_slot() -> void:
	if tile_defs.is_empty():
		return
	var d: Dictionary = tile_defs.values()[0]
	var size := Vector2i(Vector2(d.rect[2], d.rect[3]) * float(d.get("scale", 2)))
	var format := Image.FORMAT_RGBAH
	if SceneData.uses_release(d.base):
		format = SceneData.gtx_header(SceneData.gtx_path(d.base)).get("format", format)
	slot_format = format
	var hdr := Image.create_empty(size.x, size.y, true, format)
	var layers: Array[Image] = []
	for i in TILE_LAYERS:
		layers.append(hdr)
	var l8 := Image.create(size.x, size.y, false, Image.FORMAT_L8)
	_slot = {size = size, base = ImageTexture.create_from_image(hdr), groups = _array(layers),
		depth = ImageTexture.create_from_image(Image.create(size.x, size.y, false, Image.FORMAT_RF)),
		ids = ImageTexture.create_from_image(l8), puddle = ImageTexture.create_from_image(l8),
		wet = ImageTexture.create_from_image(l8)}


## Starts loading a hotspot's tile on a worker thread (no-op if it is loaded or loading).
func request_tile(hotspot_id: String) -> void:
	if not tile_defs.has(hotspot_id) or tile_ready(hotspot_id):
		return
	if _tile_task >= 0 or not _stage.is_empty():
		if _tile_pending.get("id") != hotspot_id:
			_tile_pending.next = hotspot_id
		return
	var result := {id = hotspot_id, def = tile_defs[hotspot_id]}
	_tile_pending = result
	_tile_task = WorkerThreadPool.add_task(_load_tile.bind(result), false, "load tile")


func _load_tile(result: Dictionary) -> void:
	var def: Dictionary = result.def
	var t0 := Time.get_ticks_msec()
	var paths: Array = [def.base]
	for g in def.get("groups", []):
		paths.append(g.image)
	var imgs := load_hdr_parallel(paths)
	if imgs[0] == null:
		return
	var size: Vector2i = imgs[0].get_size()
	result.base = imgs[0]
	result.group_imgs = []
	result.group_ids = []
	var tgroups: Array = def.get("groups", [])
	for i in tgroups.size():
		if imgs[i + 1]:
			result.group_imgs.append(imgs[i + 1])
			result.group_ids.append(tgroups[i].id)
	result.depth = SceneData.f32_image(def.depth, size.x, size.y)
	result.ids = _ids_image(def.get("ids", ""))
	var tm: Dictionary = def.get("masks", {})
	result.masks = {}
	for key in ["puddle", "wet"]:
		var m := SceneData.image(tm.get(key, ""))
		if m:
			m.convert(Image.FORMAT_L8)
			result.masks[key] = m
	var r: Array = def.rect
	result.rect = Rect2(r[0], r[1], r[2], r[3])
	result.scale = Vector2(size) / result.rect.size
	result.ms = Time.get_ticks_msec() - t0


func _poll_tile() -> void:
	if not _stage.is_empty():
		var t0 := Time.get_ticks_usec()
		_stage.pop_front().call()
		_upload_us += Time.get_ticks_usec() - t0
		return
	if _tile_task < 0 or not WorkerThreadPool.is_task_completed(_tile_task):
		return
	WorkerThreadPool.wait_for_task_completion(_tile_task)
	_tile_task = -1
	var r := _tile_pending
	_tile_pending = {}
	if r.has("base") and r.base.get_size() == _slot.size and r.base.get_format() == slot_format:
		_stage_upload(r)
	elif r.has("next"):
		request_tile(r.next)


## Queues the swap of tile r into the slot: one texture or array layer per frame.
func _stage_upload(r: Dictionary) -> void:
	tile = {}                       # the slot is being overwritten: not shown until done
	mat.set_shader_parameter("tile_mix", 0.0)
	_upload_us = 0
	if perf:
		perf.mark("tile %s swap" % r.id)
	var size: Vector2i = _slot.size
	var blank := Image.create(size.x, size.y, false, Image.FORMAT_L8)
	_stage.append(func(): _slot.base.update(r.base))
	for i in mini(r.group_imgs.size(), TILE_LAYERS):
		var img: Image = r.group_imgs[i]
		_stage.append(func(): _slot.groups.update_layer(img, i))
	_stage.append(func(): _slot.depth.update(r.depth))
	_stage.append(func(): _slot.ids.update(r.ids if r.ids and r.ids.get_size() == size else blank))
	for key in ["puddle", "wet"]:
		var m: Image = r.masks.get(key)
		_stage.append(func(): _slot[key].update(m if m and m.get_size() == size else blank))
	_stage.append(func():
		r.erase("group_imgs")
		r.erase("base")   # depth stays: depth_at() reads it while the tile is shown
		print("tile %s: %d groups, decoded in %d ms on a worker, uploaded over %d frames (%.0f ms on the main thread)" % [
			r.id, r.group_ids.size(), r.ms, 5 + r.group_ids.size(), _upload_us / 1000.0])
		_use_tile(r)
		if r.has("next"):
			request_tile(r.next))


func _use_tile(r: Dictionary) -> void:
	tile = r
	mat.set_shader_parameter("tile_base", _slot.base)
	mat.set_shader_parameter("tile_groups", _slot.groups)
	mat.set_shader_parameter("tile_count", r.group_ids.size())
	mat.set_shader_parameter("tile_depth", _slot.depth)
	mat.set_shader_parameter("tile_ids", _slot.ids)
	mat.set_shader_parameter("tile_puddle", _slot.puddle)
	mat.set_shader_parameter("tile_wet", _slot.wet)
	mat.set_shader_parameter("tile_rect", _uv_rect(r.rect))
	mat.set_shader_parameter("tile_lod_bias", log(r.scale.x) / log(2.0))


# ---------- per frame ----------

func update(t: float) -> void:
	_poll_tile()
	var arr := PackedFloat32Array()
	arr.resize(MAX_GROUPS)
	for i in groups.size():
		var g: Dictionary = groups[i]
		var lv := 1.0 if frozen else Curves.level(g.curve, t, g.seed)
		levels[g.id] = lv
		intensities[g.id] = pow(lv, 1.3)
		arr[i] = intensities[g.id]
	mat.set_shader_parameter("intensity", arr)
	if not wide.is_empty():
		mat.set_shader_parameter("wide_intensity", _mapped(wide.group_ids))
	if not tile.is_empty():
		mat.set_shader_parameter("tile_intensity", _mapped(tile.group_ids))
	mat.set_shader_parameter("time", t)
	mat.set_shader_parameter("highlight", highlight)
	var any := false
	for h in highlight:
		any = any or h > 0.001
	mat.set_shader_parameter("any_highlight", any)


func _mapped(ids: Array) -> PackedFloat32Array:
	var arr := PackedFloat32Array()
	arr.resize(MAX_GROUPS)
	for i in mini(ids.size(), MAX_GROUPS):
		arr[i] = intensities.get(ids[i], 0.0)
	return arr


## The camera's view: rect in frame px, the world viewport's real size, the zoom.
func set_view(view: Rect2, viewport_px: Vector2, zoom: float) -> void:
	mat.set_shader_parameter("view_rect", _uv_rect(view))
	# log2 of main-frame texels per screen pixel
	mat.set_shader_parameter("lod", log(view.size.x / viewport_px.x) / log(2.0))
	# one canvas pixel in frame uv (the outline's width is set in canvas pixels)
	mat.set_shader_parameter("px_uv", view.size / CANVAS / frame)
	tile_mix = 0.0
	if not tile.is_empty() and tile.rect.intersects(view):
		tile_mix = smoothstep(1.2, 1.7, zoom)
	mat.set_shader_parameter("tile_mix", tile_mix)


func set_rain(on: bool) -> void:
	mat.set_shader_parameter("rain", 1.0 if on else 0.0)


func intensity(id) -> float:
	return intensities.get(id, 1.0) if id != null else 1.0


func level(id) -> float:
	return levels.get(id, 1.0) if id != null else 1.0


## The group whose anchor is nearest to p, within max_m; null if none.
func nearest_group(p: Vector3, max_m := 3.0):
	var best = null
	var best_d := max_m
	for g in groups:
		var d: float = p.distance_to(g.anchor) if g.anchor != Vector3.INF else INF
		if d < best_d:
			best = g
			best_d = d
	return best


# ---------- lookups in frame px (the source the screen shows there) ----------

func _source(px: Vector2) -> String:
	if not tile.is_empty() and tile_mix > 0.5 and tile.rect.has_point(px):
		return "tile"
	if Rect2(Vector2.ZERO, frame).has_point(px):
		return "main"
	if not wide.is_empty() and wide.rect.has_point(px):
		return "wide"
	return ""


static func _pixel(img: Image, p: Vector2) -> Color:
	var x := clampi(int(p.x), 0, img.get_width() - 1)
	var y := clampi(int(p.y), 0, img.get_height() - 1)
	return img.get_pixel(x, y)


func _local(src: String, px: Vector2, img: Image) -> Vector2:
	match src:
		"tile":
			return (px - tile.rect.position) * tile.scale
		"wide":
			return (px - wide.rect.position) / wide.rect.size * Vector2(img.get_size())
	return px


## Depth of the frame at a frame pixel, in metres along the camera axis from the main camera.
func depth_at(px: Vector2) -> float:
	var src := _source(px)
	match src:
		"tile":
			return _pixel(tile.depth, _local(src, px, tile.depth)).r
		"main":
			return _pixel(depth_img, px).r
		"wide":
			return _pixel(wide.depth, _local(src, px, wide.depth)).r + wide.offset
	return 200.0


## Hotspot number (1-based, 0 = none) at a frame pixel from the ids masks; -1 without ids.
func id_at(px: Vector2) -> int:
	if ids_img == null:
		return -1
	var src := _source(px)
	var img: Image = {"tile": tile.get("ids"), "main": ids_img, "wide": wide.get("ids")}.get(src)
	if img == null:
		return 0
	return roundi(_pixel(img, _local(src, px, img)).r * 255.0)


## Puddle or wet mask (0..1) at a frame pixel of the main frame.
func mask_at(key: String, px: Vector2) -> float:
	var img: Image = masks.get(key)
	if img == null or not Rect2(Vector2.ZERO, frame).has_point(px):
		return 0.0
	return _pixel(img, px).r


## Outline strength per hotspot number (1..31).
func set_highlight(strengths: Dictionary) -> void:
	for i in MAX_IDS:
		highlight[i] = float(strengths.get(i, 0.0))
