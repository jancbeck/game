extends Control
## HUD: attribute bars (score + flexibility), active quest, interaction
## prompt, and transient messages. Redraws from store state on change.

@onready var stats_label: RichTextLabel = %StatsLabel
@onready var quest_label: Label = %QuestLabel
@onready var prompt_label: Label = %PromptLabel
@onready var message_label: Label = %MessageLabel


func _ready() -> void:
	prompt_label.hide()
	message_label.hide()


func refresh() -> void:
	var state := Store.get_state()
	var lines: Array[String] = []
	var attributes: Dictionary = state["player"]["attributes"]
	for attr_id: String in ["might", "guile", "lore", "heart"]:
		var attr: Dictionary = attributes[attr_id]
		var flex_note := (
			"hardened" if int(attr["flexibility"]) <= 0 else "flex %d" % int(attr["flexibility"])
		)
		lines.append(
			(
				"[b]%s[/b] %d  [color=gray](%s)[/color]"
				% [attr_id.capitalize(), int(attr["score"]), flex_note]
			)
		)
	stats_label.text = "\n".join(lines)
	var active: Array = state["quests"]["active"]
	if active.is_empty():
		quest_label.text = ""
	else:
		var quest: Dictionary = Db.get_quest(str(active[-1]))
		quest_label.text = "Quest: %s" % quest.get("title", str(active[-1]))


func show_prompt(text: String) -> void:
	prompt_label.text = text
	prompt_label.show()


func hide_prompt() -> void:
	prompt_label.hide()


func flash_message(text: String) -> void:
	message_label.text = text
	message_label.show()
	var tween := create_tween()
	tween.tween_interval(1.5)
	tween.tween_callback(message_label.hide)
