## The Xbox pad (any joypad Godot knows; Xbox Wireless over Bluetooth works on macOS).
##
##   left stick       walks the figure; the stick points where it goes on the screen
##   D-pad, right stick   select the next thing in that direction on the screen (nearest first)
##   A                interact with the selection; skips the line being spoken (or goes on to the next)
##   B                back: close the dialogue or the satchel, drop the selection, else open the menu
##   LB or X (held)   highlight everything, like Tab
##   Y or Menu        the satchel
##   View, RB         the character sheet, the journal (D-pad up/down: next skill, scroll)
##   D-pad up/down    in a conversation, move through the responses; A picks
##
## Logic asks for actions (actions.gd), never for raw buttons. The mouse cursor is hidden while the
## pad is in use and comes back when the mouse moves.
extends Node

const REACH_M := 12.0        # what the selection can reach, on the figure's level
const AUTO_M := 2.5          # standing this close to something selects it
const LOOK_M := 0.7          # how far ahead of the figure the stick aims on the walk mesh
const TURN_RATE := 14.0      # how fast the aim follows the stick (1/s)
const CONE := 2.2            # a candidate counts as "that way" within this much sideways per forward

var main
var active := false          # the pad is the last thing used
var driving := false         # the stick is walking the figure
var _aim := Vector3.ZERO     # smoothed ground direction of the stick


func setup(m) -> void:
	main = m


# ---------- pad or mouse ----------

func _input(event: InputEvent) -> void:
	if event is InputEventJoypadButton or (event is InputEventJoypadMotion and absf(event.axis_value) > 0.5):
		use_pad(true)
	elif (event is InputEventMouseMotion and event.relative.length() > 1.5) or event is InputEventMouseButton:
		use_pad(false)


func use_pad(on: bool) -> void:
	if on == active:
		return
	active = on
	Input.mouse_mode = Input.MOUSE_MODE_HIDDEN if on else Input.MOUSE_MODE_VISIBLE
	main.interaction.set_pad_mode(on)


# ---------- the stick walks ----------

func _blocked() -> bool:
	return main.ui.busy or main.ui.is_open() or main.portals.busy or main.inventory_ui.is_open() or main.sheet_ui.is_open() or main.menu.is_open() or main.session.traveling


func _physics_process(delta: float) -> void:
	var stick := Input.get_vector("walk_left", "walk_right", "walk_up", "walk_down")
	if _blocked() or stick == Vector2.ZERO:
		if driving:
			driving = false
			_aim = Vector3.ZERO
			main.player.stop()
			_auto_select()
		return
	use_pad(true)
	var want := ground_dir(stick)
	_aim = want if _aim == Vector3.ZERO else _aim.lerp(want, 1.0 - exp(-TURN_RATE * delta)).normalized()
	var at: Vector3 = main.player.global_position
	var goal: Vector3 = main.nav.nav_point(at + _aim * LOOK_M)
	if Vector2(goal.x - at.x, goal.z - at.z).length() < 0.04:
		# against a wall head-on: stand still instead of shuffling
		main.player.stop()
		return
	if not driving:
		driving = true
		main.interaction.pending = null
		main.portals.clear_route()
		main.interaction.set_selected(null)
	main.player.walk_to(goal)


## The ground direction (unit, Godot axes) that shows up on the screen as `stick` (x right, y down).
func ground_dir(stick: Vector2) -> Vector3:
	var bx: Vector3 = main.rig.bx
	var by: Vector3 = main.rig.by
	var s := Vector2(stick.x, -stick.y)
	var det := bx.x * by.z - bx.z * by.x
	var g := Vector3((by.z * s.x - bx.z * s.y) / det, 0.0, (-by.x * s.x + bx.x * s.y) / det)
	return g.normalized()


# ---------- selecting ----------

func _auto_select() -> void:
	if main.interaction.selected != null:
		return
	var near: Array = main.interaction.candidates(AUTO_M)
	if not near.is_empty():
		main.interaction.set_selected(near[0].target)


## Moves the selection one step in a screen direction: the nearest candidate that way, else
## around to the far end. With nothing selected it takes the nearest to the figure.
func select_step(dir: Vector2) -> void:
	var list: Array = main.interaction.candidates(REACH_M)
	if list.is_empty():
		main.interaction.set_selected(null)
		return
	var cur = main.interaction.selected
	if cur == null:
		main.interaction.set_selected(list[0].target)
		return
	var here: Vector2 = main.screen_of(main.interaction.anchor_of(cur))
	var best = null
	var best_score := INF
	var far = null
	var far_along := INF
	for c in list:
		if _same(c.target, cur):
			continue
		var d: Vector2 = main.screen_of(main.interaction.anchor_of(c.target)) - here
		var along := d.dot(dir)
		var across := absf(d.cross(dir))
		if along > 1.0 and across <= along * CONE:
			var score := along + across * 2.0
			if score < best_score:
				best_score = score
				best = c
		if along < far_along:
			far_along = along
			far = c
	var pick = best if best != null else far
	if pick != null:
		main.interaction.set_selected(pick.target)


func _same(a: Dictionary, b: Dictionary) -> bool:
	if a.kind != b.kind:
		return false
	match a.kind:
		"hotspot":
			return a.hotspot == b.hotspot
		"npc":
			return a.npc == b.npc
		"exit":
			return a.exit == b.exit
	return a.portal == b.portal and a.end == b.end


# ---------- buttons ----------

## Edges are polled: a stick held past the threshold is one press, not one per motion event.
func _process(_delta: float) -> void:
	if main.session.traveling or main.ui.busy:
		return
	var ui = main.ui
	if main.sheet_ui.is_open():
		if Input.is_action_just_pressed("menu_up") or Input.is_action_just_pressed("pick_up"):
			main.sheet_ui.move(-1)
		elif Input.is_action_just_pressed("menu_down") or Input.is_action_just_pressed("pick_down"):
			main.sheet_ui.move(1)
		return
	if main.inventory_ui.is_open():
		if Input.is_action_just_pressed("menu_left") or Input.is_action_just_pressed("pick_left"):
			main.inventory_ui.move(-1)
		elif Input.is_action_just_pressed("menu_right") or Input.is_action_just_pressed("pick_right"):
			main.inventory_ui.move(1)
		return
	if ui.is_open():
		if Input.is_action_just_pressed("menu_up") or Input.is_action_just_pressed("pick_up"):
			ui.move_option(-1)
		elif Input.is_action_just_pressed("menu_down") or Input.is_action_just_pressed("pick_down"):
			ui.move_option(1)
		elif Input.is_action_just_pressed("confirm"):
			if main.dialogue.waiting():
				main.dialogue.skip()
			else:
				ui.confirm_option()
		return
	for d in [["pick_left", Vector2.LEFT], ["pick_right", Vector2.RIGHT], ["pick_up", Vector2.UP], ["pick_down", Vector2.DOWN]]:
		if Input.is_action_just_pressed(d[0]):
			select_step(d[1])
			return
	if Input.is_action_just_pressed("confirm") and main.interaction.selected != null:
		main.interaction.act(main.interaction.selected)
