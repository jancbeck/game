// Fixture for scripts/systems_check.gd: the tags and externals of skills, checks and the journal.
// scripts/ink.py compiles it to checks.json. It is not part of the game's story.

EXTERNAL roll(skill, difficulty, kind)
EXTERNAL skill_value(skill)
EXTERNAL skill_add(skill, amount)
EXTERNAL end_chapter(id)

-> END

=== passives ===
Everyone hears this line.
A boot print, too fresh for the rain. # skill:perception # passive:10
The wall remembers a hard winter. # skill:stonework # passive:challenging
+ [\[Leave.\]] -> END

=== checks ===
+ [Press him #check:authority:18:white:calm] -> press
+ [Shout him down #check:authority:18:red] -> shout
+ [\[Leave.\]] -> END

=== press ===
{ roll("authority", 18, "white"): He gives way. | He does not. }
-> checks

=== shout ===
{ roll("authority", 18, "red"): He flinches. | He laughs at you. }
-> checks

=== journal_demo ===
Marl nods. # journal:test_task:Find the rider.
+ [Go on.] -> journal_more

=== journal_more ===
# journal:test_task:The rider sleeps in the tower.
+ [Close it.] -> journal_close
+ [\[Leave.\]] -> END

=== journal_close ===
That is that. # journal_done:test_task
+ [\[Leave.\]] -> END

=== values ===
{ skill_value("logic") >= 4: Sharp. | Dull. }
~ skill_add("logic", 1)
{ skill_value("logic") }
+ [\[Leave.\]] -> END

// For the interface check (--ui-check): the three looks of a check option.
=== showcase ===
Marl wipes his hands on his coat and does not look at you. # speaker:marl
He is lying about something small. # skill:empathy # passive:medium
The wall at his back is older than his oath. # skill:stonework # passive:easy
+ [Press him until he gives way. #check:authority:12:white:calm] -> show_press
+ [Order him to open the stores. #check:authority:13:red] -> show_order
+ [Count the spears on the rack. #check:logic:10:white] -> show_count
+ [\[Leave.\]] -> END

=== show_press ===
{ roll("authority", 12, "white"): He gives way. | He does not. }
-> showcase

=== show_order ===
{ roll("authority", 13, "red"): He hands over the key. | He laughs at you. }
-> showcase

=== show_count ===
{ roll("logic", 10, "white"): Eleven spears, and one of them is a broom. | You lose count at nine. }
-> showcase

// The end of a chapter: the lines before end_chapter are read, the ones after it never show.
=== ending ===
The last line before the card.
~ end_chapter("night_one")
This line is never shown.
-> END
