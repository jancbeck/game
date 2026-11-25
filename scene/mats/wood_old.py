"""Weathered planks soaked by the rain: dark brown-grey with a glossy film on the up-facing planes (roofs, decks, lids), moss-streaked and rotting there, lichen spots, drier and paler only under cover."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _wood  # noqa: E402


def build(mat, nt, bsdf):
    _wood.build(nt, bsdf, dark=(0.052, 0.040, 0.029), light=(0.180, 0.150, 0.114),
                edge=(0.30, 0.285, 0.26), edge_amount=0.8, rough=(0.62, 0.92), bump=0.02, tile=(0.5, 1.0),
                blotch=2.0, tone_var=0.5,
                wet_tint=(0.46, 0.40, 0.34), wet_rough=0.36, ground=0.9, streaks=0.55, film=0.85,
                roof=1.0, roof_moss=0.7, lichen=(0.60, 0.66))
