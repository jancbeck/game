# Ashen Vale

A small isometric 3D narrative RPG prototype in Godot 4.5. Gothic-inspired
penal-colony setting; Disco Elysium-inspired dialogue with visible locked
options.

**The mechanic:** you have four attributes — Might, Guile, Lore, Heart.
Every time you solve a problem with one of them, that attribute grows and
the *flexibility* of the other three shrinks. Reach zero flexibility and
that attribute is hardened: options that would need it to grow are locked
for the rest of the run. Specialists cut deep but end up with exactly one
way to finish the story; generalists keep their options and their doubts.

## Playing

Open the project in Godot 4.5 (or run `godot --path .`) and play. WASD to
move, E to talk, J to open the journal (quest log + recorded entries),
F5/F9 quick save/load. Talk to Rurik at the gate, earn
your place with Marda, deal with the chained man, then face the Overseer.
Four endings, gated by what you've made of yourself.

## Verifying

Everything is authored as text (scripts, scenes, JSON content) and verified
headless — no editor GUI required:

```sh
pip install "gdtoolkit==4.*"
gdlint scripts/ test/ tools/ && gdformat --check scripts/ test/ tools/
godot --headless --import
godot --headless -s tools/smoke_test.gd     # boots the real game, plays a quest, saves/loads
# unit + integration suites run via gdUnit4 (see .github/workflows/ci.yml)
```

CI runs all of the above on every push. See `CLAUDE.md` for the project
rules and `docs/` for design notes.
