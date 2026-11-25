## The game camera's zoom: one orthographic camera with the export's direction, moved in its own
## plane and narrowed or widened, so the frame, the 3D world and every overlay stay registered.
##
## The view is a rectangle in main-frame pixels (2560 x 1440 at zoom 1): zoom 0.5 shows the wide
## view (twice the frame's width and height around the same centre), zoom 2 a quarter of the
## frame around an object. Depth stays valid at every zoom: the camera only moves across its own
## axis, so the frame's depth along that axis does not change.
##
## The title screen holds the intro at its wide view (`hold_intro`), where it drifts by a few percent
## and back; `begin_intro` lets the ease start from wherever the drift has got to.
##
## Motion: the intro eases the zoom from 0.5 to 1 over intro_s with a quintic ease in and out;
## focus() and release() then move zoom (in log space) and centre with a critically damped spring,
## which can be retargeted halfway without a jolt.
##
## Coordinates: "screen px" are canvas pixels (input events, UI; always 2560 x 1440 here) and
## "frame px" are pixels of the main frame. screen_to_frame() and frame_to_screen() convert.
extends Node

const SceneData := preload("res://scripts/scene_data.gd")

signal settled

var cam: Camera3D
var frame := Vector2(2560, 1440)
var origin: Vector3            # main camera origin (frame centre)
var bx: Vector3
var by: Vector3
var fwd: Vector3
var ppm := 73.14
var width_m := 35.0

var zoom := 1.0
var centre := Vector2(1280, 720)        # frame px at the screen centre
var _target_zoom := 1.0
var _target_centre := Vector2(1280, 720)
var _vel_logz := 0.0
var _vel_c := Vector2.ZERO
var smooth_s := 0.9                     # spring time constant
var intro_s := 7.0
var intro_from := 0.5
var _intro_t := -1.0
var _was_moving := false
var held := false                       # the intro waits at its wide view (title screen)
var _held_t := 0.0

const HELD_DRIFT := 0.07                # the held view breathes in by this much of its zoom ...
const HELD_PERIOD_S := 80.0             # ... and out again over this long


func setup(data: SceneData, camera: Camera3D, cfg: Dictionary) -> void:
	cam = camera
	var c: Dictionary = data.scene.camera
	frame = Vector2(data.frame_size())
	origin = SceneData.v3(c.origin)
	bx = SceneData.v3(c.basis_x)
	by = SceneData.v3(c.basis_y)
	fwd = -SceneData.v3(c.basis_z).normalized()
	ppm = float(c.px_per_m)
	width_m = float(c.ortho_width_m)
	centre = frame * 0.5
	_target_centre = centre
	intro_s = float(cfg.get("intro_s", 7.0))
	intro_from = float(cfg.get("intro_zoom", 0.5))
	smooth_s = float(cfg.get("smooth_s", 0.9))
	if cfg.get("intro", true) and intro_s > 0.0:
		_intro_t = 0.0
		zoom = intro_from
	_apply()


## Ease to zoom z centred on frame point c (clamped so the view stays inside the frame).
func focus(c: Vector2, z: float) -> void:
	_intro_t = -1.0
	_target_zoom = z
	_target_centre = c


func release() -> void:
	focus(frame * 0.5, 1.0)


## Jump without easing (capture runs).
func set_view(c: Vector2, z: float) -> void:
	_intro_t = -1.0
	zoom = z
	_target_zoom = z
	centre = _clamp_centre(c, z)
	_target_centre = centre
	_vel_logz = 0.0
	_vel_c = Vector2.ZERO
	_apply()


func in_intro() -> bool:
	return _intro_t >= 0.0


## Keeps the intro at its wide view, drifting slowly, until begin_intro().
func hold_intro() -> void:
	if _intro_t < 0.0:
		return
	held = true
	_held_t = 0.0


## Plays the held intro from the zoom it stands at.
func begin_intro() -> void:
	if not held:
		return
	held = false
	intro_from = zoom
	_intro_t = 0.0


func update(delta: float) -> void:
	if held:
		_held_t += delta
		zoom = intro_from * (1.0 + HELD_DRIFT * (0.5 - 0.5 * cos(_held_t * TAU / HELD_PERIOD_S)))
		centre = frame * 0.5
	elif _intro_t >= 0.0:
		_intro_t += delta
		var u := clampf(_intro_t / intro_s, 0.0, 1.0)
		var e := u * u * u * (u * (u * 6.0 - 15.0) + 10.0)   # quintic: no velocity at either end
		zoom = exp(lerpf(log(intro_from), 0.0, e))
		centre = frame * 0.5
		if u >= 1.0:
			_intro_t = -1.0
			_target_zoom = 1.0
			_target_centre = centre
			settled.emit()
	else:
		var lz := _damp(log(zoom), log(_target_zoom), delta)
		zoom = exp(lz)
		var tc := _clamp_centre(_target_centre, _target_zoom)
		centre = _damp2(centre, tc, delta)
		var moving := absf(log(zoom / _target_zoom)) > 0.002 or centre.distance_to(tc) > 0.5
		if _was_moving and not moving:
			settled.emit()
		_was_moving = moving
	_apply()


# critically damped spring (one state per axis)
func _damp(x: float, target: float, dt: float) -> float:
	var w := 2.0 / smooth_s
	var e := exp(-w * dt)
	var d := x - target
	var tmp := (_vel_logz + w * d) * dt
	_vel_logz = (_vel_logz - w * tmp) * e
	return target + (d + tmp) * e


func _damp2(x: Vector2, target: Vector2, dt: float) -> Vector2:
	var w := 2.0 / smooth_s
	var e := exp(-w * dt)
	var d := x - target
	var tmp := (_vel_c + w * d) * dt
	_vel_c = (_vel_c - w * tmp) * e
	return target + (d + tmp) * e


func _clamp_centre(c: Vector2, z: float) -> Vector2:
	if z <= 1.0:
		return frame * 0.5
	var half := frame / z * 0.5
	return Vector2(clampf(c.x, half.x, frame.x - half.x), clampf(c.y, half.y, frame.y - half.y))


func _apply() -> void:
	if cam == null:
		return
	cam.size = width_m / zoom
	var off := (centre - frame * 0.5) / ppm
	cam.global_transform = Transform3D(cam.global_basis, origin + bx * off.x - by * off.y)


## The view as a rect in frame px.
func view_rect() -> Rect2:
	var s := frame / zoom
	return Rect2(centre - s * 0.5, s)


## Main-frame px of a world point (independent of the current view).
func frame_px_of(p: Vector3) -> Vector2:
	var rel := p - origin
	return Vector2(rel.dot(bx) * ppm + frame.x * 0.5, frame.y * 0.5 - rel.dot(by) * ppm)


func screen_to_frame(p: Vector2) -> Vector2:
	var r := view_rect()
	return r.position + p / frame * r.size


func frame_to_screen(p: Vector2) -> Vector2:
	var r := view_rect()
	return (p - r.position) / r.size * frame
