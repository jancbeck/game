## Rain as individual drops (GPU particles): each drop falls at its own terminal velocity, is
## pushed by the wind at its own position with its own lag and turbulence, and splashes where it
## reaches the frame's visible surface, where the same particle becomes its splash
## (rain_process.gdshader, rain_draw.gdshader). Gust bands travel downwind across
## the courtyard; nothing moves the whole field at once.
##
## Drops are born at TOP_M over the area the camera sees at zoom min(z, 1), widened upwind for
## the drift, at a constant rate per square metre: the wide intro view has four times the drops of
## the main view, and zooming in to 2 keeps the main view's drops, so zooming back out finds rain
## everywhere. Ripples in puddles and the faint splashes on wet stone stay in background.gdshader.
## Toward zoom 0.5 the streaks stretch to WIDE_STREAK_PX along their fall and fade (rain_draw.gdshader).
##
## config.json -> rain {drops (alive at zoom 1), fall_m_s [min, max], wind_mean_m_s,
## wind_gust_m_s, gust_speed_m_s, turbulence_m_s, splash_share, intensity}.
extends Node3D

const SceneData := preload("res://scripts/scene_data.gd")
const TOP_M := 15.0      # birth height above the courtyard floor; above the towers (11 m)
const LIFETIME := 2.9    # s; a drop falls 15 m + the 3 m lower ward in about 2.6 s at 7 m/s
const UPWIND_M := 9.0    # how far upwind of the view drops are born (gust drift over a fall)
const MAX_ZOOM_OUT := 0.5
const WIDE_STREAK_PX := 24.0   # streak length on screen at zoom 0.5, in px of the frame

var drops: GPUParticles3D
var proc: ShaderMaterial
var draw_mat: ShaderMaterial
var rig
var per_view := 22000
var _area_1 := 1.0


func setup(camera_rig, comp, cfg: Dictionary) -> void:
	rig = camera_rig
	per_view = int(cfg.get("drops", 22000))
	proc = ShaderMaterial.new()
	proc.shader = load("res://shaders/rain_process.gdshader")
	var fall: Array = cfg.get("fall_m_s", [7.0, 9.0])
	proc.set_shader_parameter("fall_min", float(fall[0]))
	proc.set_shader_parameter("fall_max", float(fall[1]))
	proc.set_shader_parameter("wind_mean", float(cfg.get("wind_mean_m_s", 1.0)))
	proc.set_shader_parameter("wind_gust", float(cfg.get("wind_gust_m_s", 3.4)))
	proc.set_shader_parameter("gust_speed", float(cfg.get("gust_speed_m_s", 7.0)))
	proc.set_shader_parameter("turbulence", float(cfg.get("turbulence_m_s", 0.7)))
	proc.set_shader_parameter("splash_share", float(cfg.get("splash_share", 0.6)))
	proc.set_shader_parameter("cam_origin", rig.origin)
	proc.set_shader_parameter("cam_x", rig.bx)
	proc.set_shader_parameter("cam_y", rig.by)
	proc.set_shader_parameter("cam_fwd", rig.fwd)
	proc.set_shader_parameter("px_per_m", rig.ppm)
	proc.set_shader_parameter("frame_size", rig.frame)
	proc.set_shader_parameter("depth_tex", ImageTexture.create_from_image(comp.depth_img))
	proc.set_shader_parameter("puddle_tex", ImageTexture.create_from_image(comp.masks.puddle))
	if not comp.wide.is_empty():
		var r: Rect2 = comp.wide.rect
		proc.set_shader_parameter("wide_on", true)
		proc.set_shader_parameter("wide_rect", Vector4(r.position.x, r.position.y, r.size.x, r.size.y))
		proc.set_shader_parameter("wide_depth", ImageTexture.create_from_image(comp.wide.depth))
		proc.set_shader_parameter("wide_offset", comp.wide.offset)

	_area_1 = _spawn_area(1.0)
	var amount := int(per_view * _spawn_area(MAX_ZOOM_OUT) / _area_1)

	draw_mat = ShaderMaterial.new()
	draw_mat.shader = load("res://shaders/rain_draw.gdshader")
	draw_mat.set_shader_parameter("intensity", float(cfg.get("intensity", 1.0)))
	var quad := QuadMesh.new()
	quad.size = Vector2.ONE
	quad.material = draw_mat

	drops = GPUParticles3D.new()
	drops.name = "Drops"
	drops.amount = amount
	drops.lifetime = LIFETIME
	drops.preprocess = LIFETIME
	drops.process_material = proc
	drops.draw_pass_1 = quad
	drops.local_coords = false
	drops.visibility_aabb = AABB(Vector3(-200, -50, -200), Vector3(400, 120, 400))
	drops.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(drops)
	_update_spawn()
	drops.emitting = true
	print("rain: %d drops at zoom 1, up to %d at zoom %.1f" % [per_view, amount, MAX_ZOOM_OUT])


## Birth area for the view at zoom z (centred on the frame): the screen rect, stretched up by
## the height a drop falls through and upwind by its drift, projected onto the plane y = TOP_M.
## Returns three corners: origin, +x end, +y end.
func _spawn_quad(z: float) -> Array:
	var view_size: Vector2 = rig.frame / z
	var c: Vector2 = rig.frame * 0.5
	var fall_px: float = (TOP_M + 3.5) * absf(rig.by.y) * rig.ppm
	var x0: float = c.x - view_size.x * 0.5 - UPWIND_M * rig.ppm
	var x1: float = c.x + view_size.x * 0.5 + 1.5 * rig.ppm
	var y0: float = c.y - view_size.y * 0.5 - fall_px - 1.0 * rig.ppm
	var y1: float = c.y + view_size.y * 0.5 + 1.0 * rig.ppm
	return [_on_top(Vector2(x0, y0)), _on_top(Vector2(x1, y0)), _on_top(Vector2(x0, y1))]


func _on_top(px: Vector2) -> Vector3:
	var p: Vector3 = rig.origin + rig.bx * (px.x - rig.frame.x * 0.5) / rig.ppm + rig.by * (rig.frame.y * 0.5 - px.y) / rig.ppm
	return p + rig.fwd * (TOP_M - p.y) / rig.fwd.y


func _spawn_area(z: float) -> float:
	var q := _spawn_quad(z)
	return (q[1] - q[0]).cross(q[2] - q[0]).length()


func _update_spawn() -> void:
	var z: float = minf(rig.zoom, 1.0)
	var q := _spawn_quad(z)
	proc.set_shader_parameter("spawn_o", q[0])
	proc.set_shader_parameter("spawn_a", q[1] - q[0])
	proc.set_shader_parameter("spawn_b", q[2] - q[0])
	drops.amount_ratio = clampf(_spawn_area(z) / _area_1 * per_view / drops.amount, 0.0, 1.0)


func update(t: float, compositor) -> void:
	_update_spawn()
	proc.set_shader_parameter("clock", t)
	var px_per_m: float = rig.ppm * rig.zoom * float(get_viewport().size.x) / rig.frame.x
	draw_mat.set_shader_parameter("px_per_m", px_per_m)
	draw_mat.set_shader_parameter("wide", clampf((1.0 - rig.zoom) / (1.0 - MAX_ZOOM_OUT), 0.0, 1.0))
	draw_mat.set_shader_parameter("wide_len_px", WIDE_STREAK_PX * float(get_viewport().size.x) / rig.frame.x)
	var fires := []
	for g in compositor.groups:
		if g.curve == "fire" and g.anchor != Vector3.INF and fires.size() < 4:
			fires.append(Vector4(g.anchor.x, g.anchor.y, g.anchor.z, compositor.intensity(g.id)))
	draw_mat.set_shader_parameter("fires", fires)
	draw_mat.set_shader_parameter("fire_count", fires.size())


## The wide view's depth goes with compositor.drop_wide().
func drop_wide() -> void:
	proc.set_shader_parameter("wide_on", false)
	proc.set_shader_parameter("wide_depth", null)
