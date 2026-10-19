"""Capability: the rubber type style, one of the Type family
(videobuilder.type): rubber letters, letters drop, squash, stretch and
settle on springs, then hop in turn. Every style's demo sets the same three
lines in the same three colours (_type.py), so they compare.

    python -m videobuilder preview examples/capabilities/type-rubber.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _type  # noqa: E402
import videobuilder as vb  # noqa: E402

FILM = _type.film('rubber')

if __name__ == '__main__':
    vb.main(__file__)
