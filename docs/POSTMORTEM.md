# Postmortem: the first prototype (Nov 2025)

The previous iteration of this repo (see git history before the 2026
rewrite) attempted a multi-agent workflow — PM, WRITER, CODER, ARCHITECT
roles orchestrated via prompt instructions. It produced a clean ~1,500-LOC
reducer core and a working quest pipeline, and then collapsed. Root causes,
and the countermeasure now baked into this repo:

1. **Self-reported status.** Dashboards claimed an "NPCSystem" with 36
   passing tests that never existed in the codebase.
   → Status lives only in CI results; prose status docs are banned.
2. **The validator couldn't look.** The PM role was forbidden from reading
   code or running anything, making validation a rubber stamp.
   → Whoever claims something works must run the proof.
3. **Post-mortem without fix.** A correctly diagnosed character-file
   serialization bug was documented and never fixed; broken files shipped.
   → A diagnosis and its fix land in the same PR or not at all.
4. **Editor-centric dependency.** Dialogic 2 fought the code-only
   constraint (GUI workflows, hand-unwritable resource formats) and was
   the single biggest churn source.
   → Own the dialogue runner (~100 lines); no editor-only addons.
5. **Doc accretion.** Two contradicting PROJECT_STATUS files, specs for
   systems that were never built.
   → Delete stale docs; specs live next to the validator that enforces them.
6. **Asset pipeline overreach.** AI-generated 3D models + third-party
   animation library = rig mismatch hell.
   → Procedural primitives only; atmosphere from lighting.
