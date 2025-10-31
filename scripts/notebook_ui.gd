extends CanvasLayer

@onready var entries_label : RichTextLabel = $Panel/VBox/Entries

func _ready() -> void:
    WorldState.connect("notebook_updated", Callable(self, "_refresh"))
    _refresh()

func toggle() -> void:
    visible = not visible
    if visible:
        _refresh()

func _refresh() -> void:
    var lines : Array[String] = []
    for entry in WorldState.notebook_entries:
        lines.append("• %s" % entry)
    entries_label.text = "\n\n".join(lines)
