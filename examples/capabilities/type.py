"""Capability family: Type (videobuilder.type). The same three lines played
in a few of the styles in turn, each running its own enter, hold and exit:
the family card's demo. Each style has its own demo beside this one
(type-<name>.py).

    python -m videobuilder preview examples/capabilities/type.py

Longer than STYLE.md's 2-4 s on purpose: four styles, 3 s each (STYLE.md's
note on the Type family).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _type  # noqa: E402
import videobuilder as vb  # noqa: E402

FILM = _type.relay_film()

if __name__ == '__main__':
    vb.main(__file__)
