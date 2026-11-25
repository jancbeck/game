## Quest flags and variables: one store for the game and the story. A name the story declares with
## VAR is that Ink variable (so conditions in the ink see what the game sets, and the other way
## round); any other name is kept here. Both go into the save.
##
##   main.quest.set_flag("bell_rung")   main.quest.flag("bell_rung")   main.quest.get_flag("count", 0)
extends RefCounted

signal changed(name: String)

var story = null            # story.gd, once loaded
var extra := {}             # flags the story does not declare


func set_flag(name: String, value = true) -> void:
	if story != null and story.has_var(name):
		story.set_var(name, value)
	else:
		extra[name] = value
	changed.emit(name)


func get_flag(name: String, default = false):
	if story != null and story.has_var(name):
		return story.get_var(name)
	return extra.get(name, default)


## True when the flag is set to something truthy.
func flag(name: String) -> bool:
	return bool(get_flag(name, false))


## Every story variable and extra flag, for the F1 panel.
func all() -> Dictionary:
	var out := {}
	if story != null:
		for n in story.variable_names():
			out[n] = story.get_var(n)
	out.merge(extra)
	return out
