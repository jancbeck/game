// The story of the game. One file per person, included below; the knots are entry points:
//   talk_<npc id>   the conversation with that person (data/npcs/<id>.json)
//   look_<hotspot>  runs instead of the hotspot's static look text when the player examines it
// Compile with `python3 scripts/ink.py` after every change; the game reads main.json.
//
// Tags on a line:
//   # line:<clip id>      voices the line with the speaker's clip (assets/npcs/<speaker>/<clip id>.wav)
//   # speaker:<npc id>    who says it; without it the person you talk to speaks, and at a hotspot
//                         the line is narration. `# speaker:narrator` makes a line narration anywhere.
// A choice written \[Like this.\] is an action and is not echoed into the log as speech.
//   # skill:<id>           a skill speaks the line (data/skills.json); with
//   # passive:<n or name>  as well it is heard only when the skill + 6 reaches n ("medium", 10)
//   # journal:<task>:<text>   writes the task into the journal; # journal_done:<task> closes it
// A choice can carry a check, written inside its brackets: + [Press him #check:authority:12:white]
// (white may be tried again once the skill has risen or the named flag, a fourth field, is set; red
// once only). Its body makes the roll: { roll("authority", 12, "white"): success | failure }.
//
// Variables are the quest state: they are saved, shown in the F1 panel, and readable from the
// game as main.quest.get_flag("name").

VAR met_marl = false
VAR bell_looked = false
// Quest "The rider nobody rang for" (quest.ink). rider: 0 not started, 1 asked by Marl,
// 2 seal found, 3 linen found, 4 Hedda confessed, 5 letter taken, 6 told Marl.
VAR rider = 0
VAR seal_found = false
VAR rag_found = false
VAR marl_knows_hedda = false
VAR letter_outcome = ""
VAR tam_woken = false
VAR knows_ford = false
VAR tam_wants_commander = false
// The commander (commander.ink)
VAR commander_met = false
VAR letter_delivered = false
VAR player_claim = ""

-> END

INCLUDE marl.ink
INCLUDE hedda.ink
INCLUDE quest.ink
INCLUDE tam.ink
INCLUDE commander.ink
INCLUDE interiors.ink

// The game binds these (scripts/story.gd). The bodies are for testing in Inky.
EXTERNAL give_item(item)
EXTERNAL take_item(item)
EXTERNAL has_item(item)
EXTERNAL set_flag(name, value)
EXTERNAL get_flag(name)
EXTERNAL play_line(speaker, clip)
EXTERNAL roll(skill, difficulty, kind)
EXTERNAL skill_value(skill)
EXTERNAL skill_add(skill, amount)
EXTERNAL end_chapter(id)

=== function give_item(item) ===
~ return
=== function take_item(item) ===
~ return
=== function has_item(item) ===
~ return false
=== function set_flag(name, value) ===
~ return
=== function get_flag(name) ===
~ return false
=== function play_line(speaker, clip) ===
~ return
=== function roll(skill, difficulty, kind) ===
~ return false
=== function skill_value(skill) ===
~ return 0
=== function skill_add(skill, amount) ===
~ return

=== function end_chapter(id) ===
~ return
