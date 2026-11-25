## Flipbook elements over the frame: flames, smoke, mist. Each atlas plays in its pixel rect of
## the frame, at its depth, with its blend mode, and its brightness follows its light group.
##
## scene.json -> flipbooks [{id, atlas, cols, rows, frames, fps, loop, rect, blend, depth, depth_m,
## group, cell?, encoding?, scale?}]. Atlas cells are row-major from the top left. With encoding
## "srgb" (the default) the PNG holds sRGB-encoded linear values: rgb = srgb_to_linear(png) * scale.
## Blend "add": under + rgb. "premul": rgb + (1 - a) * under. "alpha": straight alpha.
##
## An entry whose id ends in "@2" ("density": 2) is the same element at twice the density, for
## the zoom tiles only: while a tile is shown (compositor tile_mix) and the element lies inside
## it, the @2 entry replaces its 1x entry; never in the main or the wide view. Rects are
## main-frame pixels for both; view_rect places them on screen at any zoom.
extends Node3D

const SceneData := preload("res://scripts/scene_data.gd")

const TEMPLATE := """
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, shadows_disabled, fog_disabled, %s;
uniform sampler2D atlas : %s, filter_linear;
uniform sampler2D depth_tex : filter_nearest;
uniform vec4 rect;          // x, y, w, h in frame pixels
uniform vec2 frame_size;
uniform vec4 view_rect = vec4(0.0, 0.0, 1.0, 1.0);   // screen -> main frame uv
uniform vec2 grid;          // cols, rows
uniform vec2 cell_uv;       // one cell's size in atlas UV
uniform float frame = 0.0;
uniform float depth_m = 40.0;
uniform float gain = 1.0;
uniform float fade = 1.0;   // cross-fade between the 1x and @2 entries
varying vec2 local;

void vertex() {
	local = vec2(VERTEX.x * 0.5 + 0.5, 0.5 - VERTEX.y * 0.5);
	vec2 px = rect.xy + local * rect.zw;
	vec2 ndc = (px / frame_size - view_rect.xy) / view_rect.zw * 2.0 - 1.0;   // clip-space y points down the frame here
	vec4 clip = PROJECTION_MATRIX * vec4(0.0, 0.0, -depth_m, 1.0);
	POSITION = vec4(ndc, clip.z / clip.w, 1.0);
}

void fragment() {
	float f = floor(frame);
	vec2 cell = vec2(mod(f, grid.x), floor(f / grid.x));
	vec2 uv = (cell + clamp(local, 0.001, 0.999)) * cell_uv;
	vec4 c = texture(atlas, uv);
	%s
	ALBEDO = c.rgb * gain * %s;
	ALPHA = %s;
}
"""

var books: Array = []   # [{def, mat, node}]
var compositor


func setup(data: SceneData, comp) -> void:
	compositor = comp
	var fs := Vector2(data.frame_size())
	for fb in data.scene.get("flipbooks", []):
		var img := SceneData.image(fb.atlas)
		if img == null:
			continue
		var blend: String = fb.get("blend", "add")
		var srgb: bool = fb.get("encoding", "srgb") == "srgb"
		var cols := int(fb.cols)
		var rows := int(fb.rows)
		var cell: Vector2 = Vector2(fb.cell[0], fb.cell[1]) if fb.get("cell") else Vector2(img.get_size()) / Vector2(cols, rows)
		var has_depth = fb.get("depth") != null and fb.get("depth") != ""
		var depth_code := ""
		if has_depth:
			depth_code = "vec4 dc = PROJECTION_MATRIX * vec4(0.0, 0.0, -texture(depth_tex, uv).r, 1.0); DEPTH = dc.z / dc.w;"
		var mode: String = {"add": "blend_add", "premul": "blend_premul_alpha", "alpha": "blend_mix"}.get(blend, "blend_mix")
		var alpha := "1.0" if blend == "add" else "c.a * fade"
		var rgb_fade := "1.0" if blend == "alpha" else "fade"
		var sh := Shader.new()
		sh.code = TEMPLATE % [mode, "source_color" if srgb else "hint_default_black", depth_code, rgb_fade, alpha]
		var mat := ShaderMaterial.new()
		mat.shader = sh
		mat.set_shader_parameter("atlas", ImageTexture.create_from_image(img))
		if has_depth:
			var d := SceneData.f32_image(fb.depth, img.get_width(), img.get_height())
			if d:
				mat.set_shader_parameter("depth_tex", ImageTexture.create_from_image(d))
		var r: Array = fb.rect
		mat.set_shader_parameter("rect", Vector4(r[0], r[1], r[2], r[3]))
		mat.set_shader_parameter("frame_size", fs)
		mat.set_shader_parameter("grid", Vector2(cols, rows))
		mat.set_shader_parameter("cell_uv", cell / Vector2(img.get_size()))
		mat.set_shader_parameter("depth_m", float(fb.get("depth_m", 40.0)))
		var quad := QuadMesh.new()
		quad.size = Vector2(2, 2)
		var mi := MeshInstance3D.new()
		mi.name = "flipbook_" + String(fb.id)
		mi.mesh = quad
		mi.material_override = mat
		mi.extra_cull_margin = 16384.0
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
		books.append({def = fb, mat = mat, node = mi, scale = float(fb.get("scale", 1.0)), hi = String(fb.id).ends_with("@2"),
			has_hi = false, rect = Rect2(r[0], r[1], r[2], r[3])})
	var ids := books.map(func(b): return String(b.def.id))
	for b in books:
		b.has_hi = not b.hi and ids.has(String(b.def.id) + "@2")
	# back to front: farther elements draw first, all before the rain
	var order := books.duplicate()
	order.sort_custom(func(a, b): return float(a.def.get("depth_m", 40.0)) > float(b.def.get("depth_m", 40.0)))
	for i in order.size():
		order[i].mat.render_priority = -100 + i
	print("flipbooks: %d" % books.size())


var _view := Vector4(0, 0, 1, 1)
var _tile_rect := Rect2()
var _tile_mix := 0.0


## The camera's view rect (frame px), and the shown tile's rect and blend (compositor).
func set_view(view: Rect2, frame: Vector2, tile_rect: Rect2, tile_mix: float) -> void:
	_view = Vector4(view.position.x / frame.x, view.position.y / frame.y, view.size.x / frame.x, view.size.y / frame.y)
	_tile_rect = tile_rect
	_tile_mix = tile_mix


func _hi_weight(rect: Rect2) -> float:
	return _tile_mix if _tile_mix > 0.0 and _tile_rect.encloses(rect) else 0.0


func update(t: float) -> void:
	for b in books:
		b.mat.set_shader_parameter("view_rect", _view)
		var w := 1.0
		if b.hi:
			w = _hi_weight(b.rect)
		elif b.has_hi:
			w = 1.0 - _hi_weight(b.rect)
		b.node.visible = w > 0.001
		var fb: Dictionary = b.def
		var n := int(fb.frames)
		var f := t * float(fb.get("fps", 24))
		f = fposmod(f, n) if fb.get("loop", true) else minf(f, n - 1)
		b.mat.set_shader_parameter("frame", f)
		b.mat.set_shader_parameter("fade", w)
		b.mat.set_shader_parameter("gain", b.scale * compositor.intensity(fb.get("group")))
