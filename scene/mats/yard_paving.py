"""The yard outside the cookhouse: the same flagstones as the kitchen, wet with dusk rain, standing water in patches."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flagstone  # noqa: E402


def build(mat, nt, bsdf):
    flagstone.build(mat, nt, bsdf, wet=0.85)
