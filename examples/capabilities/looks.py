"""Capability family: Looks (videobuilder.looks). The shared lighthouse
scene wiping from each look to the next, every one moving its own way: the
family card's demo. Each look has its own demo beside this one
(look-<name>.py).

    python -m videobuilder preview examples/capabilities/looks.py

Longer than STYLE.md's 2-4 s on purpose: it holds each of the eight looks
for 0.8 s (STYLE.md's note on the Looks family).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _looks  # noqa: E402
import videobuilder as vb  # noqa: E402

FILM = _looks.relay_film()

if __name__ == '__main__':
    vb.main(__file__)
