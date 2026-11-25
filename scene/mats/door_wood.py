"""Gate oak: dark soaked oak, plank-to-plank tone changes, wet foot, rust bleeding under the iron straps; the vault keeps it a little drier than the rest."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood  # noqa: E402

# bottom edges of the gate's iron straps in world meters (scene/assets/gate_door.py: centres 0.55 ... 3.7, 0.15 tall)
STRAP_BOTTOMS = (0.475, 1.275, 2.075, 2.875, 3.625)


def build(mat, nt, bsdf):
    _wood.build(nt, bsdf, dark=(0.022, 0.014, 0.009), light=(0.105, 0.068, 0.040),
                edge=(0.15, 0.12, 0.09), edge_amount=0.3, rough=(0.55, 0.85), bump=0.016, tile=(0.45, 1.2),
                blotch=1.8, tone_var=1.0,
                wet_tint=(0.50, 0.42, 0.34), wet_rough=0.3, ground=1.5, grime=0.6, streaks=0.7, film=0.8,
                mud_amount=0.5, bleed_z=STRAP_BOTTOMS)
