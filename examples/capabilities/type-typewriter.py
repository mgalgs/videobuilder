"""Capability: the typewriter type style, one of the Type family
(videobuilder.type): typewriter, letters strike in one by one, a little
uneven, the caret riding the line. Every style's demo sets the same three
lines in the same three colours (_type.py), so they compare.

    python -m videobuilder preview examples/capabilities/type-typewriter.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _type  # noqa: E402
import videobuilder as vb  # noqa: E402

FILM = _type.film('typewriter')

if __name__ == '__main__':
    vb.main(__file__)
