"""Capability: the blueprint filter look, one of the Looks family
(videobuilder.looks): a held screenshot restyled by
`looks.filter(cv, 'blueprint', t)`, with the filter's own motion. Every filter
look's demo restyles a still picture (_looks.py), so all the motion on
screen is the filter's.

    python -m videobuilder preview examples/capabilities/look-filter-blueprint.py

Its own palette is the look's (STYLE.md's style-card exception).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _looks  # noqa: E402
import videobuilder as vb  # noqa: E402

FILM = _looks.filter_film('blueprint', 'dashboard')

if __name__ == '__main__':
    vb.main(__file__)
