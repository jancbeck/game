## The pointer: a quill with an iron nib, drawn in code (supersampled polygons with a ragged
## hand-cut edge and an ink outline, so it reads against both dusk and firelight). The nib is the
## hot spot. Over something that can be interacted with the nib glows like a coal.
##
## interaction.gd already switches Godot's arrow and pointing-hand shapes with the hover, so the
## two images simply replace those shapes. Nothing is ever drawn where the player clicked.
extends RefCounted

const SIZE := 44                  # cursor image, px
const SS := 6                     # supersampling
const NIB := Vector2(5.0, 38.0)   # hot spot, in image px
const INK := Color(0.06, 0.05, 0.05, 0.96)


static func apply() -> void:
	Input.set_custom_mouse_cursor(ImageTexture.create_from_image(make(false)), Input.CURSOR_ARROW, NIB)
	Input.set_custom_mouse_cursor(ImageTexture.create_from_image(make(true)), Input.CURSOR_POINTING_HAND, NIB)


## Writes both cursors, enlarged, to `dir` for a look (see cursor_preview.gd).
static func export_preview(dir: String) -> void:
	DirAccess.make_dir_recursive_absolute(dir)
	for k in [["cursor", false], ["cursor_hover", true]]:
		var img := make(k[1])
		img.resize(SIZE * 4, SIZE * 4, Image.INTERPOLATE_NEAREST)
		img.save_png("%s/%s.png" % [dir, k[0]])


static func make(hover: bool) -> Image:
	var c := Canvas.new(SIZE, SS)
	var axis_from := Vector2(11.0, 31.0)     # where the vane begins
	var axis_to := Vector2(38.0, 4.0)        # the feather's tip
	var u := (axis_to - axis_from).normalized()
	var side := Vector2(-u.y, u.x)           # toward the lower right
	var vane := PackedVector2Array()
	var left := PackedVector2Array()
	var right := PackedVector2Array()
	var spine := PackedVector2Array()
	var steps := 30
	for i in steps + 1:
		var t := float(i) / steps
		var centre := axis_from.lerp(axis_to, t) + side * 2.2 * sin(PI * t)
		var w := 6.2 * pow(sin(PI * (0.05 + 0.9 * t)), 0.7)
		var rough := 1.0 + 0.13 * sin(t * 61.0) + 0.08 * sin(t * 103.0 + 1.3)
		var notch := 0.55 if absf(t - 0.52) < 0.035 else 1.0
		spine.append(centre)
		left.append(centre - side * w * 0.8 * rough)
		right.append(centre + side * w * 1.1 * rough * notch)
	vane.append_array(left)
	right.reverse()
	vane.append_array(right)
	var tint := Color(0.93, 0.80, 0.55) if hover else Color(0.80, 0.76, 0.67)
	# outline, then body
	c.fill(vane, INK)
	c.stroke(vane, 2.4, INK, true)
	c.fill(vane, tint)
	var shade := PackedVector2Array(left)
	spine.reverse()
	shade.append_array(spine)
	c.fill(shade, tint.darkened(0.12))
	# barbs: short strokes leaning toward the tip, a little different each time
	for k in 14:
		var t := 0.12 + 0.8 * k / 13.0
		var centre := axis_from.lerp(axis_to, t) + side * 2.2 * sin(PI * t)
		var w := 6.2 * pow(sin(PI * (0.05 + 0.9 * t)), 0.7)
		for s in [-0.7, 0.9]:
			var jitter := 0.85 + 0.3 * sin(k * 7.3 + s)
			c.line(centre + u * 0.5, centre + side * s * w * 0.85 * jitter + u * 2.4, 0.55, Color(0.38, 0.33, 0.26, 0.55))
	c.line(axis_from - u * 0.5, axis_to - u * 1.0, 1.25, Color(0.34, 0.28, 0.21))
	# the bare quill and the iron nib
	var base := axis_from + u * 0.5
	var tip := NIB
	var barrel := PackedVector2Array([base + side * 1.9, base - side * 1.9, tip + u * 3.4 - side * 0.9, tip + u * 3.4 + side * 0.9])
	c.fill(barrel, INK)
	c.stroke(barrel, 2.2, INK, true)
	c.fill(barrel, Color(0.88, 0.82, 0.64))
	var nib := PackedVector2Array([tip + u * 4.4 + side * 1.2, tip + u * 4.4 - side * 1.2, tip])
	c.fill(nib, INK)
	c.stroke(nib, 2.0, INK, true)
	c.fill(nib, Color(0.42, 0.44, 0.48))
	c.line(tip + u * 0.8, tip + u * 4.0, 0.5, Color(0.80, 0.82, 0.85))
	if hover:
		c.glow(tip + u * 0.4, 5.5, Color(1.0, 0.55, 0.15, 0.85))
		c.disc(tip + u * 0.2, 1.1, Color(1.0, 0.9, 0.6))
	return c.finish()


## A supersampled RGBA canvas with polygon fills, drawn in image px.
class Canvas:
	var img: Image
	var n: int
	var ss: int

	func _init(size: int, supersample: int) -> void:
		n = size
		ss = supersample
		img = Image.create(size * ss, size * ss, false, Image.FORMAT_RGBA8)
		img.fill(Color(0, 0, 0, 0))

	## Even-odd scanline fill of a polygon given in image px.
	func fill(poly: PackedVector2Array, c: Color) -> void:
		var pts := PackedVector2Array()
		for p in poly:
			pts.append(p * ss)
		var y0 := maxi(0, int(floor(_min_y(pts))))
		var y1 := mini(img.get_height() - 1, int(ceil(_max_y(pts))))
		for y in range(y0, y1 + 1):
			var yc := y + 0.5
			var xs: Array[float] = []
			for i in pts.size():
				var a := pts[i]
				var b := pts[(i + 1) % pts.size()]
				if (a.y <= yc) != (b.y <= yc):
					xs.append(a.x + (yc - a.y) / (b.y - a.y) * (b.x - a.x))
			xs.sort()
			for k in range(0, xs.size() - 1, 2):
				for x in range(maxi(0, int(ceil(xs[k] - 0.5))), mini(img.get_width() - 1, int(floor(xs[k + 1] - 0.5))) + 1):
					_put(x, y, c)

	func _min_y(pts: PackedVector2Array) -> float:
		var m := INF
		for p in pts:
			m = minf(m, p.y)
		return m

	func _max_y(pts: PackedVector2Array) -> float:
		var m := -INF
		for p in pts:
			m = maxf(m, p.y)
		return m

	func line(a: Vector2, b: Vector2, width: float, c: Color) -> void:
		var d := (b - a).normalized().orthogonal() * width * 0.5
		fill(PackedVector2Array([a + d, b + d, b - d, a - d]), c)

	func stroke(poly: PackedVector2Array, width: float, c: Color, closed := false) -> void:
		for i in poly.size() - (0 if closed else 1):
			line(poly[i], poly[(i + 1) % poly.size()], width, c)
			disc(poly[i], width * 0.5, c)

	func disc(centre: Vector2, r: float, c: Color) -> void:
		var pts := PackedVector2Array()
		for i in 18:
			pts.append(centre + Vector2.from_angle(TAU * i / 18.0) * r)
		fill(pts, c)

	## A soft round glow: alpha falls off from the centre to the radius.
	func glow(centre: Vector2, r: float, c: Color) -> void:
		var cs := centre * ss
		var rs := r * ss
		for y in range(maxi(0, int(cs.y - rs)), mini(img.get_height(), int(cs.y + rs) + 1)):
			for x in range(maxi(0, int(cs.x - rs)), mini(img.get_width(), int(cs.x + rs) + 1)):
				var d := Vector2(x + 0.5, y + 0.5).distance_to(cs) / rs
				if d < 1.0:
					_put(x, y, Color(c, c.a * pow(1.0 - d, 1.6)))

	func _put(x: int, y: int, c: Color) -> void:
		if c.a >= 0.999:
			img.set_pixel(x, y, c)
			return
		var o := img.get_pixel(x, y)
		var a := c.a + o.a * (1.0 - c.a)
		if a <= 0.0:
			return
		img.set_pixel(x, y, Color((c.r * c.a + o.r * o.a * (1.0 - c.a)) / a, (c.g * c.a + o.g * o.a * (1.0 - c.a)) / a,
			(c.b * c.a + o.b * o.a * (1.0 - c.a)) / a, a))

	## Box-filters down to the final size in premultiplied space.
	func finish() -> Image:
		var out := Image.create(n, n, false, Image.FORMAT_RGBA8)
		var cnt := float(ss * ss)
		for y in n:
			for x in n:
				var r := 0.0
				var g := 0.0
				var b := 0.0
				var a := 0.0
				for sy in ss:
					for sx in ss:
						var p := img.get_pixel(x * ss + sx, y * ss + sy)
						r += p.r * p.a
						g += p.g * p.a
						b += p.b * p.a
						a += p.a
				out.set_pixel(x, y, Color(r / a, g / a, b / a, a / cnt) if a > 0.0 else Color(0, 0, 0, 0))
		return out
