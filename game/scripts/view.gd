## The frame on screen: a SubViewport that renders the 3D world in linear HDR at the window's
## own resolution (the export's 16:9 frame fitted, letterboxed when the aspect differs), and a
## full-window rect that applies the main still's compositor post and Blender's view transform
## through a baked 3D LUT.
##
## The post (scene.json -> layers.post, from build_scene.setup_post) runs in Blender's order:
## HueSat saturation, Glare bloom, ColorBalance lift/gamma/gain, vignette. Blender ran it on the
## render before the view exposure, so the runtime divides by 2^exposure_applied_ev first. Bloom
## takes two passes: a rect draws the highlights, and the display rect reads them back from the
## blurred screen mip levels, both inside an HDR 2D SubViewport ("Post"); the window shows its
## display values as they are.
##
## Coordinates: "frame pixels" are pixels of the export frame (2560 x 1440), whatever the window
## size. Input events arrive in frame pixels because the root window stretches canvas items to
## that base size. The SubViewport renders at the real pixel size, so conversions between frame
## pixels and viewport pixels go through frame_to_view() and view_to_frame().
extends Node

const SceneData := preload("res://scripts/scene_data.gd")
# Godot's 3D tonemap may clamp at 1; the world is scaled down by this before it and back up in
# the LUT pass, so highlights up to PRESCALE reach the view transform intact.
const PRESCALE := 16.0
# Blender 5 Glare "Bloom", strength 0.6, size 0.6, fitted as a sum of Gaussians of sigma
# 1, 2, 4 ... 256 frame px over the thresholded highlights (4.7% error against Blender's own).
const BLOOM_OCTAVES := [0.0659, 0.0186, 0.0762, 0.0302, 0.0691, 0.0593, 0.0641, 0.0485, 0.0795]
const BLOOM_FIT_STRENGTH := 0.6

var sv: SubViewport
var frame: Vector2i
var post_sv: SubViewport
var display: TextureRect
var highlights: TextureRect
var mat: ShaderMaterial
var lut_info := {}
var post_on := true


func setup(data: SceneData) -> void:
	frame = data.frame_size()
	sv = SubViewport.new()
	sv.name = "World"
	sv.own_world_3d = true
	sv.use_hdr_2d = true
	sv.msaa_3d = Viewport.MSAA_2X
	sv.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	sv.positional_shadow_atlas_size = 4096
	sv.audio_listener_enable_3d = true
	add_child(sv)
	post_sv = SubViewport.new()
	post_sv.name = "Post"
	post_sv.use_hdr_2d = true
	post_sv.disable_3d = true
	post_sv.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(post_sv)
	var hmat := ShaderMaterial.new()
	hmat.shader = load("res://shaders/bloom_highlights.gdshader")
	highlights = _rect(hmat, sv.get_texture())
	post_sv.add_child(highlights)
	mat = ShaderMaterial.new()
	mat.shader = load("res://shaders/view_transform.gdshader")
	display = _rect(mat, sv.get_texture())
	post_sv.add_child(display)
	var layer := CanvasLayer.new()
	layer.layer = -1
	add_child(layer)
	layer.add_child(_rect(null, post_sv.get_texture()))
	_load_lut(data, mat)
	_setup_post(data, mat, hmat)
	get_window().size_changed.connect(_resize)
	_resize()


func _rect(m: ShaderMaterial, tex: Texture2D) -> TextureRect:
	var r := TextureRect.new()
	r.texture = tex
	r.stretch_mode = TextureRect.STRETCH_SCALE
	# a texture's size must not become the rect's minimum size: in fullscreen the world texture is
	# larger than the 2560 x 1440 canvas, and the rect would grow past the letterbox and crop
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.set_anchors_preset(Control.PRESET_FULL_RECT)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	r.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	r.material = m
	return r


func _setup_post(data: SceneData, m: ShaderMaterial, hmat: ShaderMaterial) -> void:
	var layers: Dictionary = data.scene.get("layers", {})
	var p: Dictionary = layers.get("post", {})
	post_on = not p.is_empty() and data.config.get("post", true)
	var e := pow(2.0, float(layers.get("exposure_applied_ev", 0.0)))
	var sat := float(p.get("saturation", 1.0))
	for mm in [m, hmat]:
		mm.set_shader_parameter("prescale", PRESCALE)
		mm.set_shader_parameter("exposure_gain", e)
		mm.set_shader_parameter("saturation", sat)
	hmat.set_shader_parameter("threshold", float(p.get("bloom_threshold", 1.0)))
	var w := PackedFloat32Array()
	var strength := float(p.get("bloom", 0.0))
	for x in BLOOM_OCTAVES:
		w.append(x * strength / BLOOM_FIT_STRENGTH)
	m.set_shader_parameter("bloom_weight", w)
	var g: Dictionary = p.get("grade", {})
	for key in ["lift", "gamma", "gain"]:
		var c: Array = g.get(key, [1.0, 1.0, 1.0])
		m.set_shader_parameter(key, Vector3(c[0], c[1], c[2]))
	m.set_shader_parameter("vignette", float(p.get("vignette", 0.0)))
	m.set_shader_parameter("frame_size", Vector2(frame))
	# setup_post blurs the mask 300 px; Blender's Gaussian blur of size s has sigma s / 3
	m.set_shader_parameter("vignette_sigma", 100.0)
	set_post(post_on)
	if post_on:
		print("post: saturation %.2f, bloom %.2f above %.2f, grade, vignette %.2f, before %.1f EV of exposure" % [
			sat, strength, float(p.get("bloom_threshold", 1.0)), float(p.get("vignette", 0.0)), log(e) / log(2.0)])


func set_post(on: bool) -> void:
	post_on = on
	mat.set_shader_parameter("post", on)
	highlights.visible = on


func _load_lut(data: SceneData, mat: ShaderMaterial) -> void:
	var layers: Dictionary = data.scene.get("layers", {})
	var view: String = layers.get("view_transform", "AgX")
	var look = layers.get("look")
	var name := "%s__%s" % [_slug(view), _slug(look)]
	var dir: String = data.config.get("luts", "luts")
	var meta_path := dir.path_join(name + ".json")
	mat.set_shader_parameter("prescale", PRESCALE)
	if not FileAccess.file_exists(SceneData.res(meta_path)):
		push_warning("no view LUT %s; bake it with scene/bake_view_lut.py. Falling back to plain sRGB." % meta_path)
		mat.set_shader_parameter("use_lut", false)
		return
	var meta: Dictionary = SceneData._json(meta_path)
	var n := int(meta.size)
	var bytes := FileAccess.get_file_as_bytes(SceneData.res(dir.path_join(name + ".f32")))
	var slices: Array[Image] = []
	var slice_bytes := n * n * 3 * 4
	for b in n:
		var img := Image.create_from_data(n, n, false, Image.FORMAT_RGBF, bytes.slice(b * slice_bytes, (b + 1) * slice_bytes))
		# 3-channel float textures are not sampleable on every GPU (Metal); RGBA half is
		img.convert(Image.FORMAT_RGBAH)
		slices.append(img)
	var tex := ImageTexture3D.new()
	tex.create(Image.FORMAT_RGBAH, n, n, n, false, slices)
	mat.set_shader_parameter("lut", tex)
	mat.set_shader_parameter("lut_size", float(n))
	mat.set_shader_parameter("log_min", float(meta.log_min))
	mat.set_shader_parameter("log_max", float(meta.log_max))
	mat.set_shader_parameter("mid_grey", float(meta.mid_grey))
	mat.set_shader_parameter("use_lut", true)
	lut_info = meta
	print("view transform: %s, look %s, LUT %d^3" % [view, look, n])


static func _slug(s) -> String:
	if s == null or s == "None":
		return "none"
	return String(s).to_lower().replace("agx - ", "").replace(" ", "_")


## Fit the frame's aspect into the window, in real pixels.
func _resize() -> void:
	var win := Vector2(get_window().size)
	var aspect := float(frame.x) / frame.y
	var size := win
	if win.x / win.y > aspect:
		size.x = win.y * aspect
	else:
		size.y = win.x / aspect
	sv.size = Vector2i(maxi(1, roundi(size.x)), maxi(1, roundi(size.y)))
	post_sv.size = sv.size
	if mat:
		mat.set_shader_parameter("view_scale", float(sv.size.x) / frame.x)


func frame_to_view(p: Vector2) -> Vector2:
	return p * Vector2(sv.size) / Vector2(frame)


func view_to_frame(p: Vector2) -> Vector2:
	return p * Vector2(frame) / Vector2(sv.size)
