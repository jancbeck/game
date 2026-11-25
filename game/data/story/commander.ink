// Captain Orrin Vael, the commander, in his chamber in the tower on the cliff (location `tower`).
// Clips: assets/npcs/commander/line_NN.wav.

=== talk_commander ===
{ commander_met: -> cmd_again }
~ commander_met = true
{ letter_outcome == "marl": -> cmd_after_marl }
{ has_item("letter"): -> cmd_with_letter }
-> cmd_too_early

=== cmd_too_early ===
The commander is writing by candlelight. He lifts one finger without looking up: not now. # speaker:narrator
~ commander_met = false
-> END

=== cmd_with_letter ===
Close the door behind you. The draught finds this room before it finds anyone else. People only climb my stair at night when they carry something. # line:line_01
He has not slept. The candle has been trimmed three times; the wax on the desk says so. # skill:perception # passive:9 # line:skill_01
+ [\[Give him the letter.\]] -> cmd_read
+ [Who are you?] -> cmd_who
+ [\[Leave.\]] -> cmd_bye

=== cmd_who ===
He gives you his name as if it were a rank: Captain Orrin Vael. Nineteen winters commanding this gate. # speaker:narrator
+ [\[Give him the letter.\]] -> cmd_read
+ [\[Leave.\]] -> cmd_bye

=== cmd_read ===
~ take_item("letter")
~ letter_delivered = true
# journal_done:letter
So they recall me, after nineteen years. And six men left to hold a gate built for forty. Somebody in the capital has learned to count. # line:line_03
He folds the letter along its old creases, very carefully, the way a man handles something that has already hurt him. # skill:empathy # passive:10 # line:skill_02
-> cmd_seal

=== cmd_after_marl ===
~ letter_delivered = true
Marl brought me a letter tonight, and a story about a stranger who found it. I assume the stranger is you. Stand by the fire, at least. # line:line_02
-> cmd_seal

=== cmd_seal ===
This seal was broken before it reached me. Three waves. The Wardens' mark, not the council's crown. Tell me where it happened, and tell me exactly. # line:line_04
+ {knows_ford} [At the ford. A ferryman held Tam's satchel while he watered the horse.] -> cmd_ford
+ {not knows_ford} [Not in your stable. Before. On the road. #check:logic:10:white:knows_ford] -> cmd_reason
+ {not knows_ford} [I don't know. Tam would.] -> cmd_ask_tam

=== cmd_reason ===
{ roll("logic", 10, "white"):
    -> cmd_reason_ok
- else:
    You start to explain and lose the thread somewhere between the stable and the bell. He waits. Then he does not. # speaker:narrator
    -> cmd_ask_tam
}

=== cmd_reason_ok ===
The seal half in the straw was broken clean and cold: the wax had set long before the mare stood there. A letter opened on the road, resealed badly, and opened again here by nobody. # skill:logic # line:skill_03
Where on the road does a royal courier stop long enough? Water. A ford. # skill:logic # line:skill_04
-> cmd_ford

=== cmd_ask_tam ===
Then go and ask him. Gently. He is nineteen and frightened, and frightened people remember the wrong things. # speaker:narrator # journal:letter:Captain Vael wants to know where the seal was broken. Tam, asleep on the north-west tower landing, would know.
~ commander_met = false
-> END

=== cmd_ford ===
A ferryman at the ford. The Wardens take their tolls at that ford, and they have wanted this road unwatched for as long as I have watched it. # line:line_05
I leave at first light, if I leave at all. Before then, find me that ferryman. Quietly. Marl will give you a horse if you ask him nicely. # line:line_06 # journal:ferryman:Captain Vael wants the ferryman from the ford found before first light, quietly. Marl will give me a horse.
-> cmd_identity

=== cmd_identity ===
And you. Marl says you came to count our spears. If you did, count carefully. They are all we have left. # line:line_07
He is not asking. He is giving you the chance to lie well. # skill:authority # passive:9 # line:skill_05
+ [I did come to count them.] -> cmd_claim_assessor
+ [I'm only lost.] -> cmd_claim_lost
+ [\[Say nothing. Hold his eye.\] #check:composure:12:red] -> cmd_hold

=== cmd_claim_assessor ===
~ player_claim = "assessor"
He nods once, as if a debt had been entered in the right column. # speaker:narrator
-> cmd_bye

=== cmd_claim_lost ===
~ player_claim = "lost"
Lost men do not usually find letters. He lets it pass. # speaker:narrator
-> cmd_bye

=== cmd_hold ===
{ roll("composure", 12, "red"):
    ~ player_claim = "silent"
    He looks away first. Something in his shoulders settles, as though silence were the first honest answer he has had all night. # speaker:narrator
- else:
    ~ player_claim = "flinched"
    You blink. He sees it, and files it, and says nothing either. # speaker:narrator
}
-> cmd_bye

=== cmd_bye ===
Go on. Mind the stair on your way down. The seventh step is a liar. # line:line_08
-> END

=== cmd_again ===
He is writing. He does not stop. # speaker:narrator
+ {letter_delivered} [About the ferryman...] -> cmd_again_ferry
+ [\[Leave.\]] -> END

=== cmd_again_ferry ===
First light, he says, without looking up. # speaker:narrator
-> END
