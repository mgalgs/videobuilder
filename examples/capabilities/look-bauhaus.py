"""Capability: the bauhaus look, one of the Looks family (videobuilder.looks):
the shared lighthouse scene painted by `looks.get('bauhaus')`, with its signature
motion. Every look's demo paints the same scene (_looks.py), so they compare.

    python -m videobuilder preview examples/capabilities/look-bauhaus.py

Its own palette is the look's (STYLE.md's style-card exception).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _looks  # noqa: E402
import videobuilder as vb  # noqa: E402

FILM = _looks.film('bauhaus')

if __name__ == '__main__':
    vb.main(__file__)
