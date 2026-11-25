## The input actions, registered in code so they can be tested headless. Logic anywhere in the
## game asks for an action, never for a raw key or button; a pad button or key is one line below.
##
## Xbox layout: left stick walks, D-pad or right stick moves the selection (or the response in a
## conversation), A confirms, B goes back, LB or X holds the highlight of everything, Y or the
## menu button opens the satchel, View (back) the character sheet, RB the journal.
extends RefCounted

const STICK_DEADZONE := 0.25
const NAV_DEADZONE := 0.6


static func install() -> void:
	if InputMap.has_action("confirm"):
		return
	# the left stick walks
	_axis("walk_left", JOY_AXIS_LEFT_X, -1.0, STICK_DEADZONE)
	_axis("walk_right", JOY_AXIS_LEFT_X, 1.0, STICK_DEADZONE)
	_axis("walk_up", JOY_AXIS_LEFT_Y, -1.0, STICK_DEADZONE)
	_axis("walk_down", JOY_AXIS_LEFT_Y, 1.0, STICK_DEADZONE)
	# D-pad and right stick move the selection by screen direction
	for d in [["left", JOY_BUTTON_DPAD_LEFT, JOY_AXIS_RIGHT_X, -1.0], ["right", JOY_BUTTON_DPAD_RIGHT, JOY_AXIS_RIGHT_X, 1.0],
			["up", JOY_BUTTON_DPAD_UP, JOY_AXIS_RIGHT_Y, -1.0], ["down", JOY_BUTTON_DPAD_DOWN, JOY_AXIS_RIGHT_Y, 1.0]]:
		_axis("pick_" + d[0], d[2], d[3], NAV_DEADZONE)
		_button("pick_" + d[0], d[1])
	# the left stick and D-pad also step through responses and slots
	for d in [["up", JOY_AXIS_LEFT_Y, -1.0], ["down", JOY_AXIS_LEFT_Y, 1.0], ["left", JOY_AXIS_LEFT_X, -1.0], ["right", JOY_AXIS_LEFT_X, 1.0]]:
		_axis("menu_" + d[0], d[1], d[2], NAV_DEADZONE)
	_button("menu_up", JOY_BUTTON_DPAD_UP)
	_button("menu_down", JOY_BUTTON_DPAD_DOWN)
	_button("menu_left", JOY_BUTTON_DPAD_LEFT)
	_button("menu_right", JOY_BUTTON_DPAD_RIGHT)
	_button("confirm", JOY_BUTTON_A)
	_key("confirm", KEY_ENTER)
	_key("confirm", KEY_KP_ENTER)
	_key("confirm", KEY_SPACE)
	_button("back", JOY_BUTTON_B)
	_key("back", KEY_ESCAPE)
	_button("highlight_all", JOY_BUTTON_LEFT_SHOULDER)
	_button("highlight_all", JOY_BUTTON_X)
	_key("highlight_all", KEY_TAB)
	_button("inventory", JOY_BUTTON_Y)
	_button("inventory", JOY_BUTTON_START)
	_key("inventory", KEY_I)
	_button("sheet", JOY_BUTTON_BACK)
	_key("sheet", KEY_C)
	_button("journal", JOY_BUTTON_RIGHT_SHOULDER)
	_key("journal", KEY_J)
	_key("quick_save", KEY_F5)
	_key("quick_load", KEY_F9)


static func _add(name: String, deadzone: float) -> void:
	if not InputMap.has_action(name):
		InputMap.add_action(name, deadzone)


static func _axis(name: String, axis: int, sign_: float, deadzone: float) -> void:
	_add(name, deadzone)
	var e := InputEventJoypadMotion.new()
	e.device = -1
	e.axis = axis
	e.axis_value = sign_
	InputMap.action_add_event(name, e)


static func _button(name: String, button: int) -> void:
	_add(name, 0.5)
	var e := InputEventJoypadButton.new()
	e.device = -1
	e.button_index = button
	InputMap.action_add_event(name, e)


static func _key(name: String, keycode: int) -> void:
	_add(name, 0.5)
	var e := InputEventKey.new()
	e.device = -1
	e.keycode = keycode
	InputMap.action_add_event(name, e)
