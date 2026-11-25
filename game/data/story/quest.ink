// "The rider nobody rang for": the clues at the stable and the bell; the cook (hedda.ink) and the
// courier on the north-west tower landing (tam.ink). Marl starts it (marl_offer) and ends it (marl_finale).

=== look_stable ===
{ rider == 0: Two stalls under a lean-to against the east wall, hay in the loft over the mangers, oat bin with a stone on the lid against rats. Two horses in tonight: the old bay, and a grey mare you have not seen before. -> END }
{ seal_found: The grey mare has her head in the manger. The courier's saddle is still on her, the bags hanging empty. -> END }
A grey mare stands in the second stall, lathered to the hocks, steam rising off her in the cold. A courier's saddle, the bags empty. In the straw under the stirrup, something small and red.
New shoes, and a post-house brand on her shoulder. The king's post: she has been changed at every station and ridden hard between them. # skill:perception # passive:8 # line:skill_09
+ [\[Pick it up.\]]
    ~ seal_found = true
    ~ give_item("broken_seal")
    ~ rider = 2
    Half a wax seal, broken clean. A tower over three wavy lines. Someone opened a letter here, or wanted it to look that way. # journal:rider:Half a broken seal in the stable straw: a tower over three wavy lines. And still nobody rang the bell.
    The king's post carries the council's crown. Three waves is somebody else's seal. # skill:logic # passive:12 # line:skill_10
    -> END
+ [\[Leave it.\]] -> END

=== look_bell ===
~ bell_looked = true
{ rider == 0 or rag_found: A bronze bell no bigger than a helmet, on a bracket above the watch shelter. The rope comes down through the roof boards to a knot at shoulder height. Once for a rider, twice for trouble. -> END }
A bronze bell no bigger than a helmet. The rope no longer hangs to the knot at shoulder height: somebody has hitched it up to the bracket with a strip of cloth, well out of reach.
The bracket is older than the shelter, older than the gate. This bell has been rung for riders since before your grandfather's grandfather. It has never been gagged. # skill:stonework # passive:9 # line:skill_11
+ [\[Untie it.\]]
    ~ rag_found = true
    ~ give_item("greasy_rag")
    { rider < 3:
        ~ rider = 3
    }
    A strip of linen, stiff with old fat and smelling of onions. Kitchen linen. The rope drops back to its knot. # journal:rider:Someone hitched the bell rope out of reach with greasy kitchen linen. Who wipes their hands on linen like this?
    -> END
+ [\[Leave it.\]] -> END

=== look_cookhouse ===
A lean-to against the north-west tower: oven in front, hearth at the back under a stone hood. Beside it a stair climbs to the tower door. Bread, pease pottage, salt pork on feast days.
-> END

=== look_nw_tower_stair ===
Twenty-four steps of wet stone up the west curtain, worn to a dish in the middle of every tread, and no rail on the drop side. It starts at the flank of the cookhouse and ends at the north-west tower door, where a lamp is lit.
{ rider == 4: Up on the landing by the tower door, a bundle of wet cloak that breathes. # skill:perception # passive:6 # line:skill_12 }
-> END
