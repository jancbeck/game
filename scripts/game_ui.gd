extends CanvasLayer

## Main game UI controller

var current_dialogue_system: DialogueSystem = null
var player_stats: CharacterStats = null
var player_thoughts: ThoughtCabinet = null

@onready var dialogue_panel = $DialoguePanel
@onready var dialogue_text = $DialoguePanel/VBox/DialogueText
@onready var dialogue_speaker = $DialoguePanel/VBox/Speaker
@onready var options_container = $DialoguePanel/VBox/OptionsContainer
@onready var character_sheet_panel = $CharacterSheetPanel
@onready var character_sheet_text = $CharacterSheetPanel/MarginContainer/StatsText
@onready var thought_cabinet_panel = $ThoughtCabinetPanel
@onready var thought_cabinet_text = $ThoughtCabinetPanel/MarginContainer/ThoughtsText
@onready var interact_prompt = $InteractPrompt
@onready var skill_check_notification = $SkillCheckNotification
@onready var health_bar = $StatusBars/HealthBar
@onready var morale_bar = $StatusBars/MoraleBar


func _ready():
	add_to_group("ui")
	hide_all_panels()

	# Connect to player if it exists
	await get_tree().process_frame
	var player = get_tree().get_first_node_in_group("player")
	if player:
		player_stats = player.stats
		player_thoughts = player.thought_cabinet
		update_status_bars()


func hide_all_panels():
	if dialogue_panel:
		dialogue_panel.visible = false
	if character_sheet_panel:
		character_sheet_panel.visible = false
	if thought_cabinet_panel:
		thought_cabinet_panel.visible = false
	if interact_prompt:
		interact_prompt.visible = false
	if skill_check_notification:
		skill_check_notification.visible = false


func show_dialogue(dialogue_system: DialogueSystem):
	current_dialogue_system = dialogue_system
	dialogue_panel.visible = true
	update_dialogue_display()

	# Connect signals
	if not dialogue_system.dialogue_ended.is_connected(_on_dialogue_ended):
		dialogue_system.dialogue_ended.connect(_on_dialogue_ended)
	if not dialogue_system.skill_check_result.is_connected(_on_skill_check):
		dialogue_system.skill_check_result.connect(_on_skill_check)


func update_dialogue_display():
	if not current_dialogue_system:
		return

	var node = current_dialogue_system.get_current_node()
	if not node:
		return

	dialogue_speaker.text = node.speaker
	dialogue_text.text = node.text

	# Clear old options
	for child in options_container.get_children():
		child.queue_free()

	# Add new options
	for i in range(node.options.size()):
		var option = node.options[i]
		var button = Button.new()

		var option_text = option.text
		if option.requires_skill_check:
			var skill_value = (
				player_stats.get_skill_value(option.skill_required) if player_stats else 0
			)
			option_text = (
				"[%s %d/%d] %s"
				% [
					option.skill_required.capitalize(),
					skill_value,
					option.skill_difficulty,
					option.text.replace("[" + option.skill_required.capitalize() + "]", "")
				]
			)

		button.text = option_text
		button.pressed.connect(_on_dialogue_option_selected.bind(i))
		options_container.add_child(button)


func _on_dialogue_option_selected(option_index: int):
	if current_dialogue_system:
		var continue_dialogue = current_dialogue_system.select_option(option_index)
		if continue_dialogue:
			update_dialogue_display()
		else:
			hide_dialogue()


func _on_dialogue_ended():
	hide_dialogue()


func hide_dialogue():
	dialogue_panel.visible = false
	current_dialogue_system = null

	# Tell player dialogue ended
	var player = get_tree().get_first_node_in_group("player")
	if player and player.has_method("end_dialogue"):
		player.end_dialogue()


func toggle_character_sheet():
	character_sheet_panel.visible = !character_sheet_panel.visible
	if character_sheet_panel.visible and player_stats:
		character_sheet_text.text = player_stats.get_stats_summary()


func toggle_thought_cabinet():
	thought_cabinet_panel.visible = !thought_cabinet_panel.visible
	if thought_cabinet_panel.visible and player_thoughts:
		thought_cabinet_text.text = player_thoughts.get_thoughts_summary()


func show_interact_prompt():
	if interact_prompt:
		interact_prompt.visible = true


func hide_interact_prompt():
	if interact_prompt:
		interact_prompt.visible = false


func _on_skill_check(success: bool, skill: String):
	if skill_check_notification:
		skill_check_notification.visible = true
		var label = skill_check_notification.get_node_or_null("Label")
		if label:
			if success:
				label.text = "[%s] SUCCESS!" % skill.to_upper()
				label.add_theme_color_override("font_color", Color.GREEN)
			else:
				label.text = "[%s] FAILED!" % skill.to_upper()
				label.add_theme_color_override("font_color", Color.RED)

		# Hide after 2 seconds
		await get_tree().create_timer(2.0).timeout
		if skill_check_notification:
			skill_check_notification.visible = false


func update_status_bars():
	if not player_stats:
		return

	if health_bar:
		health_bar.value = player_stats.health
	if morale_bar:
		morale_bar.value = player_stats.morale


func _process(_delta):
	# Update status bars continuously
	update_status_bars()
