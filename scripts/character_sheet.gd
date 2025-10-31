extends CanvasLayer

@onready var stats_label : RichTextLabel = $Panel/VBox/Stats
@onready var faction_label : RichTextLabel = $Panel/VBox/Factions

func _ready() -> void:
    WorldState.connect("notebook_updated", Callable(self, "_refresh"))
    WorldState.connect("faction_changed", Callable(self, "_refresh"))
    WorldState.connect("time_advanced", Callable(self, "_refresh"))
    _refresh()

func toggle() -> void:
    visible = not visible
    if visible:
        _refresh()

func _refresh(_args = null) -> void:
    var stats_text := "[b]Faith:[/b] %d\n[b]Wit:[/b] %d\n[b]Grit:[/b] %d\n[b]Guile:[/b] %d\n[b]Health:[/b] %d\n[b]Morale:[/b] %d\n[b]Time:[/b] %s" % [
        WorldState.stats["faith"],
        WorldState.stats["wit"],
        WorldState.stats["grit"],
        WorldState.stats["guile"],
        WorldState.health,
        WorldState.morale,
        WorldState.describe_time_of_day()
    ]
    stats_label.text = stats_text

    var faction_lines : Array[String] = []
    for faction_name in WorldState.faction_reputation.keys():
        var score : int = WorldState.faction_reputation[faction_name]
        faction_lines.append("[b]%s:[/b] %s" % [faction_name, _describe_reputation(score)])
    faction_label.text = "\n".join(faction_lines)

func _describe_reputation(value : int) -> String:
    match value:
        -5, -4:
            return "Reviled"
        -3, -2:
            return "Distrustful"
        -1, 0, 1:
            return "Neutral"
        2, 3:
            return "Favored"
        4, 5:
            return "Champion"
        _:
            return str(value)
