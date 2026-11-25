"""Heavy timber gone dark with age and soaked through: deep brown, glossy where water stands, streaked by runoff, a little drier under cover."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood  # noqa: E402


def build(mat, nt, bsdf):
    _wood.build(nt, bsdf, dark=(0.026, 0.020, 0.015), light=(0.120, 0.098, 0.074),
                rough=(0.6, 0.9), bump=0.02, tile=(0.6, 1.4), blotch=1.6, tone_var=0.4,
                wet_tint=(0.50, 0.42, 0.35), wet_rough=0.34, ground=0.9, streaks=0.6, film=0.85,
                lichen=(0.64, 0.69), lichen_color=(0.13, 0.15, 0.10))
