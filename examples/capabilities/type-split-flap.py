"""Capability: the split-flap type style, one of the Type family
(videobuilder.type): split-flap board, each letter flips through the
alphabet and settles, cell by cell. Every style's demo sets the same three
lines in the same three colours (_type.py), so they compare.

    python -m videobuilder preview examples/capabilities/type-split-flap.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _type  # noqa: E402
import videobuilder as vb  # noqa: E402

FILM = _type.film('split-flap')

if __name__ == '__main__':
    vb.main(__file__)
