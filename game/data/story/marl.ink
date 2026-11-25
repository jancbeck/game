// Sergeant Marl, by the gate. Clips: assets/npcs/marl/line_NN.wav.

=== talk_marl ===
{ rider >= 5 and letter_outcome == "": -> marl_finale }
{ met_marl: -> marl_again }
-> marl_greet

=== marl_greet ===
Another one through the gate after dark. Either you're lost, or somebody sent you to count our spears. # line:line_01
~ met_marl = true
He has not stood up. A sergeant who stays seated is telling you exactly what he thinks of you. # skill:authority # passive:8 # line:skill_07
-> marl_hub

=== marl_again ===
{ rider == 6: Mind how you go. | Back again. }
-> marl_hub

=== marl_hub ===
+ {rider == 0} [Who are you?] -> marl_who
+ {rider == 0} [What is this place?] -> marl_place
+ [Why do you keep the bell under your roof?] -> marl_bell
+ {rider == 0} [Is there anything I can do?] -> marl_offer
+ {rider >= 1 and rider < 5 and not rag_found} [About the rider...] -> marl_progress
+ {rag_found and not marl_knows_hedda and rider < 5} [\[Show him the strip of linen from the bell.\]] -> marl_rag
+ {letter_delivered and get_flag("ferryman_horse") != true} [The commander wants me at the ford. I need a horse.] -> marl_horse
+ [\[Leave.\]] -> marl_bye

=== marl_who ===
Sergeant Marl. Thirty-one winters on this rock, and the rock is winning. # line:line_02
-> marl_hub

=== marl_place ===
A gate, a wall, and eleven men who argue about the soup. We watch the road north. The road has done nothing interesting since the old king died. # line:line_03
-> marl_hub

=== marl_bell ===
The last man who kept that bell in the rain let it rust silent. Ring it once for a rider, twice for trouble. Three times, and I'll want to know who taught you to count. # line:line_04
-> marl_hub

=== marl_offer ===
~ rider = 1
You want to be useful? There's a grey mare in my stable that I never let in. Saddle still steaming. And nobody rang that bell. Find out who came through my gate tonight. # line:line_06 # journal:rider:Marl wants to know who came through the gate tonight. There is a grey mare in his stable, and nobody rang the bell.
-> marl_hub

=== marl_progress ===
A horse doesn't open a gate by itself. Start with the stable. Then have a look at the bell. # line:line_07
-> marl_hub

=== marl_rag ===
~ marl_knows_hedda = true
That is kitchen linen, and greasy with it. There's only one woman on this rock who wipes her hands on everything she owns. # line:line_08
-> marl_hub

=== marl_bye ===
Mind the cart on your way out, and the cook as well. Mostly the cook. # line:line_05
-> END

=== marl_finale ===
He looks at you the way he looks at the road: waiting for it to do something. # speaker:narrator
+ [\[Give him the letter.\]] -> marl_letter
+ [It was Hedda. She tied up the bell.] -> marl_only_hedda
+ {tam_wants_commander} [I'll give it to the commander myself.] -> marl_commander
+ [I found nothing.] -> marl_nothing

=== marl_letter ===
~ take_item("letter")
~ letter_outcome = "marl"
~ rider = 6
# journal_done:rider
Recalled. The commander's recalled to the capital, and we're to be cut to six men. Six men, on a wall built for forty. Well. Now you know why nobody wanted that bell rung. # line:line_09
-> END

=== marl_only_hedda ===
~ letter_outcome = "kept"
~ marl_knows_hedda = true
~ rider = 6
# journal_done:rider
# journal:letter:I still carry the courier's letter. The commander lives in the tower on the cliff.
Hedda. Of course it was Hedda. I'll have words with her. Short ones. She'll have longer ones for me. # line:line_10
-> END

=== marl_commander ===
~ letter_outcome = "commander"
~ rider = 6
# journal_done:rider
# journal:letter:I promised Tam the letter goes to the commander, in the tower on the cliff. Marl let me go, for now.
You have the face of someone carrying more than they came in with. I'll not ask tonight. But I will ask. # line:line_11
He let you keep it. He also let you see him decide to. # skill:empathy # passive:10 # line:skill_08
-> END

=== marl_nothing ===
~ letter_outcome = "kept"
~ rider = 6
# journal_done:rider
# journal:letter:I still carry the courier's letter. The commander lives in the tower on the cliff.
You have the face of someone carrying more than they came in with. I'll not ask tonight. But I will ask. # line:line_11
-> END

=== marl_horse ===
~ set_flag("ferryman_horse", true)
A horse. For the ford. In this weather. The commander's idea, I suppose, and my mare. Bring her back with four legs and I'll forgive you the rest. # line:line_12 # journal:ferryman:Marl lent me his mare. The ford is two hours north in the rain. The ferryman will not be expecting company.
He watches you go the way he watched the road all night: waiting for it to do something. # speaker:narrator
~ end_chapter("night_one")
-> END
