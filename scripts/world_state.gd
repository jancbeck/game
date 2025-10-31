extends Node

## Global state holder for player stats, factions, notebook entries, and timekeeping.
## This script is autoloaded so that any gameplay system can query or mutate the shared state.

const DEFAULT_STATS := {
    "faith": 4,
    "wit": 6,
    "grit": 5,
    "guile": 7,
}

const INTERNAL_VOICES := [
    "Paladin Discipline",
    "Shadow Mage Temptation",
    "Mercenary Pragmatism",
]

signal time_advanced(new_time_block : int)
signal notebook_updated
signal faction_changed(faction_name : String, new_value : int)

var stats : Dictionary
var morale : int = 6
var health : int = 6
var time_block : int = 0
var notebook_entries : Array[String] = []
var faction_reputation : Dictionary = {
    "Myrtanian Legion": 0,
    "Harbor Commons": 0,
    "Old Camp Remnants": 0,
    "Circle of Water": 0,
}

func _ready() -> void:
    randomize()
    reset_state()

func reset_state() -> void:
    stats = DEFAULT_STATS.duplicate(true)
    morale = 6
    health = 6
    time_block = 0
    notebook_entries.clear()
    faction_reputation = {
        "Myrtanian Legion": 0,
        "Harbor Commons": 0,
        "Old Camp Remnants": 0,
        "Circle of Water": 0,
    }
    add_notebook_entry("Report to Commander Halvor about the disappearances.")

func advance_time(blocks : int = 1) -> void:
    time_block += max(1, blocks)
    emit_signal("time_advanced", time_block)

func add_notebook_entry(entry : String) -> void:
    if entry in notebook_entries:
        return
    notebook_entries.append(entry)
    emit_signal("notebook_updated")

func adjust_faction(faction_name : String, delta : int) -> void:
    if not faction_reputation.has(faction_name):
        faction_reputation[faction_name] = 0
    faction_reputation[faction_name] = clamp(faction_reputation[faction_name] + delta, -5, 5)
    emit_signal("faction_changed", faction_name, faction_reputation[faction_name])

func get_internal_voice(skill : String) -> String:
    match skill:
        "faith":
            return INTERNAL_VOICES[0]
        "wit":
            return INTERNAL_VOICES[1]
        "grit":
            return INTERNAL_VOICES[2]
        "guile":
            return INTERNAL_VOICES[1]
        _:
            return INTERNAL_VOICES.pick_random()

func describe_time_of_day() -> String:
    var phase := time_block % 4
    match phase:
        0:
            return "Dawn patrol"
        1:
            return "Midday bustle"
        2:
            return "Evening curfew"
        3:
            return "Witching hour"
        _:
            return "Lost in time"
