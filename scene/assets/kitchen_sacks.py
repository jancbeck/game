"""Grain sacks of a garrison kitchen: the courtyard's sack clusters (assets/sack.py), in the dull dark brown burlap of a store.

Origin: the middle of the group on the floor, 1 to 1.6 m across. Every cloth and grain of the cluster is `sacking`, so nothing in it is pale: it stands in a kitchen, not in the yard. The cluster's layout and the
number of sacks come from the seed of the plan key, as for `sack`.
"""

from . import load

LIGHTS = []


class _Mats:
    """The material library with the sack cloths and the grain replaced."""

    SWAP = {"burlap": "sacking", "straw": "sacking"}

    def __init__(self, mats):
        self._mats = mats

    def __getitem__(self, key):
        return self._mats[self.SWAP.get(key, key)]


def build(kit, mats, rng):
    root = load("sack").build(kit, _Mats(mats), rng)
    root.name = "kitchen_sacks"
    return root
