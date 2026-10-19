"""Capability: the letter-cloud type style, one of the Type family
(videobuilder.type): letter cloud, letters scattered through 3D space fly
together into the words. Every style's demo sets the same three lines in the
same three colours (_type.py), so they compare.

    python -m videobuilder preview examples/capabilities/type-letter-cloud.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _type  # noqa: E402
import videobuilder as vb  # noqa: E402

FILM = _type.film('letter-cloud')

if __name__ == '__main__':
    vb.main(__file__)
