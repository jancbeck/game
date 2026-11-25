// Tam, the courier, Hedda's nephew, asleep on the landing by the north-west tower door.
// Clips: assets/npcs/tam/line_NN.wav.

=== talk_tam ===
{ rider < 4: -> tam_stranger }
{ tam_woken: -> tam_awake }
-> tam_asleep

=== tam_stranger ===
A young man asleep on the boards in a wet cloak, a satchel under his head. Somebody else's business, for now. # speaker:narrator
-> END

=== tam_asleep ===
{ rider >= 5: He sleeps on, one hand on the empty satchel. # speaker:narrator }
{ rider >= 5: -> END }
He sleeps curled on the boards, a wet cloak over him, the satchel under his head like a pillow. # speaker:narrator
The strap is loose. One hand rests on the buckle, not holding it. # skill:perception # passive:8 # line:skill_13
+ [Ease the letter out of the satchel. #check:composure:10:red] -> tam_slip
+ [\[Wake him.\]] -> tam_wake
+ [\[Let him sleep.\]] -> END

=== tam_slip ===
{ roll("composure", 10, "red"):
    -> tam_slip_ok
- else:
    -> tam_slip_fail
}

=== tam_slip_ok ===
~ give_item("letter")
~ rider = 5
Your hands are steady. The buckle gives without a sound and the letter slides out, its seal already broken: a tower over three wavy lines. Tam sleeps on. # speaker:narrator # journal:rider:I have the courier's letter. Its seal was broken before it got here. What do I tell Marl?
-> END

=== tam_slip_fail ===
The buckle clicks like a crossbow. His eyes open. # speaker:narrator
-> tam_wake

=== tam_wake ===
~ tam_woken = true
Who's there? Don't touch that. It's for the commander, that is, and it was sealed when they gave it me. I swear it was. # line:line_01
-> tam_hub

=== tam_awake ===
Tam sits with his back to the door, hugging his knees, watching you. # speaker:narrator
-> tam_hub

=== tam_hub ===
+ {not knows_ford} [Then who broke the seal?] -> tam_seal
+ [Hedda sent me.] -> tam_hedda
+ {rider < 5} [Give me the letter.] -> tam_give
+ {rider < 5} [I'll make sure the commander gets it. #check:empathy:9:white] -> tam_trust
+ [\[Leave him.\]] -> END

=== tam_seal ===
~ knows_ford = true
It was broken at the ford. A man in a grey ferryman's cloak held my satchel while I watered the horse. When he gave it back, the wax was split. # line:line_02
A ferryman at a ford, with time enough to read a letter. The fords belong to the Wardens of the Three Waters. So does that seal. # skill:logic # passive:10 # line:skill_14
-> tam_hub

=== tam_hedda ===
Please, don't tell the sergeant. Aunt Hedda tied the bell for me. If anyone hangs for it, let it be me and not her. # line:line_03
He means it. He also hopes you will not take him up on it. # skill:empathy # passive:8 # line:skill_15
-> tam_hub

=== tam_give ===
-> tam_letter

=== tam_trust ===
{ roll("empathy", 9, "white"):
    -> tam_letter
- else:
    He pulls the satchel closer and shakes his head. Not you, not yet. # speaker:narrator
    -> tam_hub
}

=== tam_letter ===
~ give_item("letter")
~ rider = 5
~ tam_wants_commander = true
Take it, then. I'm too tired to fight you and too scared to sleep. Only give it to the commander, will you? Not to Marl. # line:line_04 # journal:rider:Tam gave me the letter and asked me to bring it to the commander, not to Marl. Its seal was broken at the ford.
-> END
