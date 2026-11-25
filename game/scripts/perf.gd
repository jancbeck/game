## Frame-time overlay and log. F3 shows or hides the overlay; the log runs always.
##
## Overlay: fps, mean and worst frame time and the 1% low over the last 5 s, draw calls, video
## memory, and the last hitch. Log: logs/perf.csv (game/logs/, not in git; the user folder in an
## exported app), one row per 5 s
## (mean, p99, worst frame, fps, 1% low fps, video memory) plus one row per hitch, a frame over
## HITCH_MS, with the last event that was marked (e.g. "tile forge").
extends CanvasLayer

const WINDOW_S := 5.0
const HITCH_MS := 50.0

var label: Label
var _times := PackedFloat32Array()     # frame times in ms over the window
var _t := 0.0
var _since := 0.0
var _last_hitch := ""
var _event := ""
var _event_t := -10.0
var _log: FileAccess


func _ready() -> void:
	layer = 20
	label = Label.new()
	label.position = Vector2(16, 12)
	label.add_theme_font_size_override("font_size", 22)
	label.add_theme_color_override("font_color", Color(0.85, 0.95, 0.8))
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 6)
	label.visible = false
	add_child(label)
	# an exported app cannot write beside its data: its log goes to the user folder
	var dir := ProjectSettings.globalize_path("res://logs" if OS.has_feature("editor") else "user://logs")
	DirAccess.make_dir_recursive_absolute(dir)
	var path := dir.path_join("perf.csv")
	var fresh := not FileAccess.file_exists(path)
	_log = FileAccess.open(path, FileAccess.READ_WRITE if not fresh else FileAccess.WRITE)
	if _log:
		_log.seek_end()
		if fresh:
			_log.store_line("time,kind,mean_ms,p99_ms,worst_ms,fps,low1_fps,video_mb,event")
		_log.store_line("%s,start,,,,,,,%s" % [Time.get_datetime_string_from_system(),
			"%dx%d" % [get_viewport().get_visible_rect().size.x, get_viewport().get_visible_rect().size.y]])


## One "startup" row: ms since the engine started when loading finished (mean column) and when
## the first frame was drawn (p99 column), and the video memory then.
func startup(loaded_ms: int, first_frame_ms: int, vram_mb: float) -> void:
	_row("startup", loaded_ms, first_frame_ms, first_frame_ms, "", 0.0, 0.0, vram_mb)


## Names what just happened, so a hitch in the next second can be blamed on it.
func mark(event: String) -> void:
	_event = event
	_event_t = _t


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F3:
		label.visible = not label.visible


func _process(delta: float) -> void:
	var ms := delta * 1000.0
	_t += delta
	_since += delta
	_times.append(ms)
	if ms > HITCH_MS and _t > 3.0:
		var cause := _event if _t - _event_t < 1.5 else ""
		_last_hitch = "%.0f ms%s" % [ms, " (%s)" % cause if cause else ""]
		_row("hitch", ms, ms, ms, cause)
	if _since < WINDOW_S:
		if label.visible:
			_draw(false)
		return
	_since = 0.0
	_draw(true)
	_times = PackedFloat32Array()


func _stats() -> Dictionary:
	var s := _times.duplicate()
	s.sort()
	var n := s.size()
	if n == 0:
		return {}
	var total := 0.0
	for v in s:
		total += v
	var p99: float = s[mini(n - 1, int(n * 0.99))]
	return {mean = total / n, p99 = p99, worst = s[n - 1], fps = 1000.0 * n / total, low1 = 1000.0 / p99}


func _draw(window_end: bool) -> void:
	var st := _stats()
	if st.is_empty():
		return
	var vram := Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0
	if window_end:
		_row("window", st.mean, st.p99, st.worst, "", st.fps, st.low1, vram)
	if label.visible:
		label.text = "%.0f fps  %.1f ms  (1%% low %.0f fps, worst %.0f ms)\ndraw calls %d  video %.0f MB\nlast hitch: %s" % [
			st.fps, st.mean, st.low1, st.worst,
			Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), vram,
			_last_hitch if _last_hitch else "none"]


func _row(kind: String, mean: float, p99: float, worst: float, event: String, fps := 0.0, low := 0.0, vram := 0.0) -> void:
	if _log:
		_log.store_line("%s,%s,%.1f,%.1f,%.1f,%.0f,%.0f,%.0f,%s" % [Time.get_datetime_string_from_system(),
			kind, mean, p99, worst, fps, low, vram, event])
		_log.flush()
