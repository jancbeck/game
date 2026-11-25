// Hedda, the cook, in the cookhouse. Clips: assets/npcs/hedda/line_NN.wav.

=== talk_hedda ===
{ hedda_greet: -> hedda_again }
-> hedda_greet

=== hedda_greet ===
Shut that door, you're letting the rain into my bread. Who let you in? No, don't tell me. Marl. Marl lets anything in. # line:line_01
-> hedda_hub

=== hedda_again ===
She does not look up from the pot. # speaker:narrator
-> hedda_hub

=== hedda_hub ===
+ {not hedda_who} [Who are you?] -> hedda_who
+ {rider >= 1 and rider < 4 and not hedda_rider} [Did a rider come through tonight?] -> hedda_rider
+ {rag_found and rider < 4} [\[Hold up the greasy linen from the bell rope.\]] -> hedda_confess
+ {hedda_rider and rider >= 1 and rider < 4 and not rag_found} [Somebody fed that rider. Somebody kind. #check:empathy:11:white:rag_found] -> hedda_press
+ {rider >= 4 and rider < 5} [Where is Tam now?] -> hedda_where
+ [\[Leave.\]] -> hedda_bye

=== hedda_who ===
Hedda. I cook. I've cooked for three commanders and buried two of them, and the third one won't eat his greens. # line:line_02
-> hedda_hub

=== hedda_rider ===
Rider? What rider. I've been up to my elbows in pease since vespers. Did you see a rider? No. Then there wasn't one. # line:line_03
Two bowls drying by the basin. A spoon still in one. She has not been eating alone. # skill:perception # passive:9 # line:skill_06
-> hedda_hub

=== hedda_press ===
{ roll("empathy", 11, "white"):
    She stops stirring. For a long moment she looks at you as if you had come in with mud on your boots and somehow not tracked it in. # speaker:narrator
    -> hedda_confess
- else:
    She laughs, a sound like a cart on gravel, and goes back to her pot. # speaker:narrator
    -> hedda_hub
}

=== hedda_confess ===
~ rider = 4
That's my linen. Fine. It was Tam, my sister's boy. He rides for the king's post, and he wouldn't let go of his letter, not even to eat. # line:line_04 # journal:rider:Hedda's nephew Tam brought a letter for the commander and asked her to keep the bell quiet. He sleeps under the timber watch hood by the north-west tower door, up the stair beside the cookhouse.
+ [Why tie up the bell?] -> hedda_why

=== hedda_why ===
He begged me. Said the letter's for the commander's eyes, and if the bell rang, Marl would have it open before the boy got his boots off. So I tied it. One knot. I've tied worse on worse men. # line:line_05
-> hedda_where

=== hedda_where ===
Up the tower stair, in the watch hood, asleep with the satchel under his head like a pillow. Wake him, and I'll salt your soup till midsummer. # line:line_06
-> hedda_hub

=== hedda_bye ===
Go on, then. And wipe your feet. This floor has seen more blood than you have, and it's still cleaner. # line:line_07
-> END
