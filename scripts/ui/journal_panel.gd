extends Control
## Narrative HUD: a toggleable panel that shows the quest log (active +
## completed quests, with the approach taken) and the journal (recorded
## entries, newest first). Data comes from the store; quest titles/summaries
## from Db. Styled to match the dialogue panel. Hidden until toggled open.

@onready var quest_label: RichTextLabel = %QuestLogLabel
@onready var journal_label: RichTextLabel = %JournalLabel


func _ready() -> void:
	hide()


func is_open() -> bool:
	return visible


func toggle() -> void:
	if visible:
		close()
	else:
		open()


func open() -> void:
	refresh()
	show()


func close() -> void:
	hide()


func refresh() -> void:
	var state := Store.get_state()
	quest_label.text = _format_quests(state)
	journal_label.text = _format_journal(state)


func _format_quests(state: Dictionary) -> String:
	var rows: Array = Reducers.quest_log(state)
	if rows.is_empty():
		return "[color=gray]No quests yet.[/color]"
	var lines: Array[String] = []
	for row: Dictionary in rows:
		var quest: Dictionary = Db.get_quest(str(row["id"]))
		var title: String = str(quest.get("title", row["id"]))
		var summary: String = str(quest.get("summary", ""))
		if row["done"]:
			var approach: String = str(row["approach"])
			var suffix := " [color=gray](%s)[/color]" % approach if not approach.is_empty() else ""
			lines.append("[color=gray]✓ %s[/color]%s" % [title, suffix])
		else:
			lines.append("[b]▸ %s[/b]" % title)
			if not summary.is_empty():
				lines.append("   [color=#b8b0a0]%s[/color]" % summary)
	return "\n".join(lines)


func _format_journal(state: Dictionary) -> String:
	var entries: Array = Reducers.journal_log(state)
	if entries.is_empty():
		return "[color=gray]Your journal is empty.[/color]"
	var lines: Array[String] = []
	for entry: String in entries:
		lines.append("• %s" % entry)
	return "\n\n".join(lines)
